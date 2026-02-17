"""Comprehensive test suite for the Employee Management API."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use in-memory SQLite for tests
os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from app.database import get_db, seed_departments
from app.main import app
from app.models import Base

TEST_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_db():
    """Create fresh tables before each test, drop after."""
    Base.metadata.create_all(bind=engine)
    # Seed departments
    db = TestingSessionLocal()
    from app.models import Department

    if db.query(Department).count() == 0:
        departments = [
            {"name": "Engineering", "code": "ENG"},
            {"name": "Human Resources", "code": "HR"},
            {"name": "Finance", "code": "FIN"},
            {"name": "Marketing", "code": "MKT"},
            {"name": "Sales", "code": "SLS"},
            {"name": "Information Technology", "code": "IT"},
            {"name": "Operations", "code": "OPS"},
        ]
        for dept_data in departments:
            db.add(Department(**dept_data))
        db.commit()
    db.close()
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


# ==========================================
# HEALTH CHECK TESTS
# ==========================================


class TestHealthCheck:
    def test_health_returns_200(self):
        r = client.get("/health")
        assert r.status_code == 200

    def test_health_response_structure(self):
        r = client.get("/health")
        data = r.json()
        assert data["status"] == "healthy"
        assert data["version"] == "1.0.0"
        assert "timestamp" in data

    def test_health_timestamp_is_valid(self):
        r = client.get("/health")
        data = r.json()
        # Should be ISO format datetime string
        assert "T" in data["timestamp"]


# ==========================================
# DEPARTMENT TESTS
# ==========================================


class TestDepartments:
    def test_list_departments_returns_200(self):
        r = client.get("/api/v1/departments")
        assert r.status_code == 200

    def test_list_departments_returns_7_seeded(self):
        r = client.get("/api/v1/departments")
        data = r.json()
        assert len(data) == 7

    def test_department_has_correct_structure(self):
        r = client.get("/api/v1/departments")
        dept = r.json()[0]
        assert "id" in dept
        assert "name" in dept
        assert "code" in dept
        assert "employee_count" in dept

    def test_department_codes_are_correct(self):
        r = client.get("/api/v1/departments")
        codes = {d["code"] for d in r.json()}
        expected = {"ENG", "HR", "FIN", "MKT", "SLS", "IT", "OPS"}
        assert codes == expected

    def test_department_employee_count_starts_at_zero(self):
        r = client.get("/api/v1/departments")
        for dept in r.json():
            assert dept["employee_count"] == 0

    def test_department_employee_count_increases_after_create(self):
        client.post(
            "/api/v1/employees",
            json={
                "first_name": "Test",
                "last_name": "User",
                "email": "test@company.com",
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        )
        r = client.get("/api/v1/departments")
        eng = next(d for d in r.json() if d["code"] == "ENG")
        assert eng["employee_count"] == 1


# ==========================================
# CREATE EMPLOYEE TESTS
# ==========================================


class TestCreateEmployee:
    def test_create_employee_returns_201(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Eduardo",
                "last_name": "Tavares",
                "email": "eduardo@company.com",
                "department_id": 1,
                "position": "RPA Engineer",
                "salary": 10000.00,
            },
        )
        assert r.status_code == 201

    def test_create_employee_response_structure(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Ana",
                "last_name": "Silva",
                "email": "ana@company.com",
                "department_id": 2,
                "position": "HR Manager",
                "salary": 9000,
            },
        )
        data = r.json()
        assert data["id"] is not None
        assert data["first_name"] == "Ana"
        assert data["last_name"] == "Silva"
        assert data["email"] == "ana@company.com"
        assert data["department_id"] == 2
        assert data["position"] == "HR Manager"
        assert data["is_active"] is True
        assert data["created_at"] is not None
        assert data["updated_at"] is None

    def test_create_employee_salary_as_decimal(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Carlos",
                "last_name": "Lima",
                "email": "carlos@company.com",
                "department_id": 3,
                "position": "Accountant",
                "salary": 7500.50,
            },
        )
        data = r.json()
        # Salary should preserve decimal precision
        assert "7500.5" in str(data["salary"])

    def test_create_employee_default_is_active_true(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Maria",
                "last_name": "Santos",
                "email": "maria@company.com",
                "department_id": 1,
                "position": "QA",
                "salary": 6000,
            },
        )
        assert r.json()["is_active"] is True

    def test_create_employee_is_active_false(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Pedro",
                "last_name": "Costa",
                "email": "pedro@company.com",
                "department_id": 1,
                "position": "Intern",
                "salary": 2000,
                "is_active": False,
            },
        )
        assert r.json()["is_active"] is False

    def test_create_duplicate_email_returns_409(self):
        payload = {
            "first_name": "Dup",
            "last_name": "User",
            "email": "dup@company.com",
            "department_id": 1,
            "position": "Dev",
            "salary": 5000,
        }
        client.post("/api/v1/employees", json=payload)
        r = client.post("/api/v1/employees", json=payload)
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"]

    def test_create_invalid_department_returns_404(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Bad",
                "last_name": "Dept",
                "email": "baddept@company.com",
                "department_id": 999,
                "position": "Dev",
                "salary": 5000,
            },
        )
        assert r.status_code == 404
        assert "Department 999 not found" in r.json()["detail"]

    def test_create_missing_required_field_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={"first_name": "Incomplete"},
        )
        assert r.status_code == 422

    def test_create_invalid_email_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Bad",
                "last_name": "Email",
                "email": "not-an-email",
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        )
        assert r.status_code == 422

    def test_create_negative_salary_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Bad",
                "last_name": "Salary",
                "email": "badsalary@company.com",
                "department_id": 1,
                "position": "Dev",
                "salary": -100,
            },
        )
        assert r.status_code == 422

    def test_create_zero_salary_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Zero",
                "last_name": "Salary",
                "email": "zerosalary@company.com",
                "department_id": 1,
                "position": "Dev",
                "salary": 0,
            },
        )
        assert r.status_code == 422

    def test_create_empty_first_name_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "",
                "last_name": "Test",
                "email": "empty@company.com",
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        )
        assert r.status_code == 422

    def test_create_department_id_zero_returns_422(self):
        r = client.post(
            "/api/v1/employees",
            json={
                "first_name": "Test",
                "last_name": "Zero",
                "email": "zero@company.com",
                "department_id": 0,
                "position": "Dev",
                "salary": 5000,
            },
        )
        assert r.status_code == 422


# ==========================================
# GET EMPLOYEE TESTS
# ==========================================


class TestGetEmployee:
    def _create_employee(self, email="get@company.com"):
        return client.post(
            "/api/v1/employees",
            json={
                "first_name": "Get",
                "last_name": "Test",
                "email": email,
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        ).json()

    def test_get_employee_returns_200(self):
        emp = self._create_employee()
        r = client.get(f"/api/v1/employees/{emp['id']}")
        assert r.status_code == 200

    def test_get_employee_data_matches(self):
        emp = self._create_employee()
        r = client.get(f"/api/v1/employees/{emp['id']}")
        data = r.json()
        assert data["first_name"] == "Get"
        assert data["last_name"] == "Test"
        assert data["email"] == "get@company.com"

    def test_get_nonexistent_employee_returns_404(self):
        r = client.get("/api/v1/employees/99999")
        assert r.status_code == 404
        assert "not found" in r.json()["detail"]


# ==========================================
# UPDATE EMPLOYEE TESTS
# ==========================================


class TestUpdateEmployee:
    def _create_employee(self, email="update@company.com"):
        return client.post(
            "/api/v1/employees",
            json={
                "first_name": "Update",
                "last_name": "Test",
                "email": email,
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        ).json()

    def test_update_single_field(self):
        emp = self._create_employee()
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"position": "Senior Dev"},
        )
        assert r.status_code == 200
        assert r.json()["position"] == "Senior Dev"
        # Other fields unchanged
        assert r.json()["first_name"] == "Update"
        assert r.json()["salary"] == "5000.00"

    def test_update_multiple_fields(self):
        emp = self._create_employee()
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"first_name": "Updated", "salary": 15000, "is_active": False},
        )
        assert r.status_code == 200
        data = r.json()
        assert data["first_name"] == "Updated"
        assert data["is_active"] is False

    def test_update_sets_updated_at(self):
        emp = self._create_employee()
        assert emp["updated_at"] is None
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"position": "Lead"},
        )
        assert r.json()["updated_at"] is not None

    def test_update_nonexistent_returns_404(self):
        r = client.put(
            "/api/v1/employees/99999",
            json={"position": "Ghost"},
        )
        assert r.status_code == 404

    def test_update_invalid_department_returns_404(self):
        emp = self._create_employee()
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"department_id": 999},
        )
        assert r.status_code == 404
        assert "Department 999 not found" in r.json()["detail"]

    def test_update_duplicate_email_returns_409(self):
        emp1 = self._create_employee("upd1@company.com")
        emp2 = self._create_employee("upd2@company.com")
        r = client.put(
            f"/api/v1/employees/{emp2['id']}",
            json={"email": "upd1@company.com"},
        )
        assert r.status_code == 409
        assert "already exists" in r.json()["detail"]

    def test_update_own_email_is_allowed(self):
        emp = self._create_employee("own@company.com")
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"email": "own@company.com"},
        )
        assert r.status_code == 200

    def test_update_change_department(self):
        emp = self._create_employee("dept_change@company.com")
        assert emp["department_id"] == 1
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={"department_id": 3},
        )
        assert r.status_code == 200
        assert r.json()["department_id"] == 3

    def test_update_empty_body(self):
        emp = self._create_employee("empty_upd@company.com")
        r = client.put(
            f"/api/v1/employees/{emp['id']}",
            json={},
        )
        # Should succeed, nothing changes
        assert r.status_code == 200
        assert r.json()["first_name"] == "Update"


# ==========================================
# DELETE EMPLOYEE TESTS
# ==========================================


class TestDeleteEmployee:
    def _create_employee(self, email="del@company.com"):
        return client.post(
            "/api/v1/employees",
            json={
                "first_name": "Delete",
                "last_name": "Test",
                "email": email,
                "department_id": 1,
                "position": "Dev",
                "salary": 5000,
            },
        ).json()

    def test_delete_returns_204(self):
        emp = self._create_employee()
        r = client.delete(f"/api/v1/employees/{emp['id']}")
        assert r.status_code == 204

    def test_delete_removes_employee(self):
        emp = self._create_employee()
        client.delete(f"/api/v1/employees/{emp['id']}")
        r = client.get(f"/api/v1/employees/{emp['id']}")
        assert r.status_code == 404

    def test_delete_nonexistent_returns_404(self):
        r = client.delete("/api/v1/employees/99999")
        assert r.status_code == 404

    def test_delete_twice_returns_404(self):
        emp = self._create_employee("del2@company.com")
        client.delete(f"/api/v1/employees/{emp['id']}")
        r = client.delete(f"/api/v1/employees/{emp['id']}")
        assert r.status_code == 404

    def test_delete_reduces_department_count(self):
        emp = self._create_employee("delcount@company.com")
        # Check count before
        depts = client.get("/api/v1/departments").json()
        eng_before = next(d for d in depts if d["code"] == "ENG")
        count_before = eng_before["employee_count"]

        client.delete(f"/api/v1/employees/{emp['id']}")

        depts = client.get("/api/v1/departments").json()
        eng_after = next(d for d in depts if d["code"] == "ENG")
        assert eng_after["employee_count"] == count_before - 1


# ==========================================
# LIST EMPLOYEES + PAGINATION + FILTERS
# ==========================================


class TestListEmployees:
    def _seed_employees(self):
        """Create a batch of employees for testing list/filter/pagination."""
        employees = [
            {"first_name": "Alice", "last_name": "Engineering", "email": "alice@co.com", "department_id": 1, "position": "Dev", "salary": 8000, "is_active": True},
            {"first_name": "Bob", "last_name": "Engineering", "email": "bob@co.com", "department_id": 1, "position": "Lead Dev", "salary": 12000, "is_active": True},
            {"first_name": "Carol", "last_name": "HR", "email": "carol@co.com", "department_id": 2, "position": "HR Analyst", "salary": 7000, "is_active": True},
            {"first_name": "David", "last_name": "Finance", "email": "david@co.com", "department_id": 3, "position": "Analyst", "salary": 9000, "is_active": False},
            {"first_name": "Eve", "last_name": "Marketing", "email": "eve@co.com", "department_id": 4, "position": "Designer", "salary": 6000, "is_active": True},
        ]
        for emp in employees:
            client.post("/api/v1/employees", json=emp)

    def test_list_returns_200(self):
        r = client.get("/api/v1/employees")
        assert r.status_code == 200

    def test_list_empty_returns_structure(self):
        r = client.get("/api/v1/employees")
        data = r.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "page_size" in data
        assert "total_pages" in data
        assert data["total"] == 0
        assert data["items"] == []
        assert data["total_pages"] == 1

    def test_list_returns_all_employees(self):
        self._seed_employees()
        r = client.get("/api/v1/employees")
        assert r.json()["total"] == 5

    def test_pagination_page_1(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?page=1&page_size=2")
        data = r.json()
        assert len(data["items"]) == 2
        assert data["total"] == 5
        assert data["page"] == 1
        assert data["page_size"] == 2
        assert data["total_pages"] == 3

    def test_pagination_page_2(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?page=2&page_size=2")
        data = r.json()
        assert len(data["items"]) == 2
        assert data["page"] == 2

    def test_pagination_last_page(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?page=3&page_size=2")
        data = r.json()
        assert len(data["items"]) == 1
        assert data["page"] == 3

    def test_pagination_beyond_last_page(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?page=100&page_size=2")
        data = r.json()
        assert len(data["items"]) == 0

    def test_filter_by_department(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?department_id=1")
        data = r.json()
        assert data["total"] == 2
        for emp in data["items"]:
            assert emp["department_id"] == 1

    def test_filter_by_is_active_true(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?is_active=true")
        data = r.json()
        assert data["total"] == 4
        for emp in data["items"]:
            assert emp["is_active"] is True

    def test_filter_by_is_active_false(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?is_active=false")
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["first_name"] == "David"

    def test_search_by_first_name(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?search=alice")
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["first_name"] == "Alice"

    def test_search_by_last_name(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?search=Engineering")
        data = r.json()
        assert data["total"] == 2  # Alice and Bob

    def test_search_by_email(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?search=carol@co.com")
        data = r.json()
        assert data["total"] == 1
        assert data["items"][0]["email"] == "carol@co.com"

    def test_search_case_insensitive(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?search=ALICE")
        assert r.json()["total"] == 1

    def test_search_no_results(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?search=zzzznotfound")
        assert r.json()["total"] == 0

    def test_combined_filters(self):
        self._seed_employees()
        r = client.get("/api/v1/employees?department_id=1&is_active=true")
        data = r.json()
        assert data["total"] == 2

    def test_invalid_page_size_too_large_returns_422(self):
        r = client.get("/api/v1/employees?page_size=101")
        assert r.status_code == 422

    def test_invalid_page_zero_returns_422(self):
        r = client.get("/api/v1/employees?page=0")
        assert r.status_code == 422


# ==========================================
# OPENAPI / DOCS TESTS
# ==========================================


class TestOpenAPI:
    def test_openapi_json_available(self):
        r = client.get("/openapi.json")
        assert r.status_code == 200
        data = r.json()
        assert data["info"]["title"] == "Employee Management API"

    def test_docs_page_available(self):
        r = client.get("/docs")
        assert r.status_code == 200

    def test_openapi_has_all_paths(self):
        r = client.get("/openapi.json")
        paths = r.json()["paths"]
        assert "/health" in paths
        assert "/api/v1/employees" in paths
        assert "/api/v1/employees/{employee_id}" in paths
        assert "/api/v1/departments" in paths

    def test_openapi_has_tags(self):
        r = client.get("/openapi.json")
        data = r.json()
        # Check tags exist in endpoint definitions
        health_get = data["paths"]["/health"]["get"]
        assert "Health" in health_get["tags"]

        emp_get = data["paths"]["/api/v1/employees"]["get"]
        assert "Employees" in emp_get["tags"]

        dept_get = data["paths"]["/api/v1/departments"]["get"]
        assert "Departments" in dept_get["tags"]
