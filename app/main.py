"""FastAPI application entry point."""

import math
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from typing import Optional

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, init_db, seed_departments
from app.models import Department, Employee
from app.schemas import (
    DepartmentResponse,
    EmployeeCreate,
    EmployeeListResponse,
    EmployeeResponse,
    EmployeeUpdate,
    ErrorResponse,
    HealthResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and seed data on startup."""
    init_db()
    seed_departments()
    yield


app = FastAPI(
    title="Employee Management API",
    description=(
        "A production-ready API for managing employees and departments. "
        "Designed to be consumed as a **Custom Connector** in Microsoft Power Platform "
        "(Power Automate, Power Apps)."
    ),
    version=settings.APP_VERSION,
    contact={
        "name": "Eduardo Tavares",
        "url": "https://github.com/SunFlower-Nz",
    },
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# --- Health Check ---

@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["Health"],
    summary="Health Check",
    description="Check if the API is running and healthy.",
)
async def health_check():
    return HealthResponse(
        status="healthy",
        version=settings.APP_VERSION,
        timestamp=datetime.now(UTC),
    )


# --- Employee Endpoints ---

@app.get(
    "/api/v1/employees",
    response_model=EmployeeListResponse,
    tags=["Employees"],
    summary="List Employees",
    description="Get a paginated list of employees with optional filters.",
)
async def list_employees(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    department_id: Optional[int] = Query(None, description="Filter by department"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    search: Optional[str] = Query(None, description="Search by name or email"),
    db: Session = Depends(get_db),
):
    query = db.query(Employee)

    if department_id is not None:
        query = query.filter(Employee.department_id == department_id)
    if is_active is not None:
        query = query.filter(Employee.is_active == is_active)
    if search:
        search_term = f"%{search}%"
        query = query.filter(
            (Employee.first_name.ilike(search_term))
            | (Employee.last_name.ilike(search_term))
            | (Employee.email.ilike(search_term))
        )

    total = query.count()
    total_pages = math.ceil(total / page_size) if total > 0 else 1
    items = query.offset((page - 1) * page_size).limit(page_size).all()

    return EmployeeListResponse(
        items=[EmployeeResponse.model_validate(emp) for emp in items],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@app.post(
    "/api/v1/employees",
    response_model=EmployeeResponse,
    status_code=201,
    tags=["Employees"],
    summary="Create Employee",
    description="Create a new employee record.",
    responses={
        409: {"model": ErrorResponse, "description": "Email already exists"},
        404: {"model": ErrorResponse, "description": "Department not found"},
    },
)
async def create_employee(
    employee: EmployeeCreate,
    db: Session = Depends(get_db),
):
    # Check if email already exists
    existing = db.query(Employee).filter(Employee.email == employee.email).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Email {employee.email} already exists")

    # Check if department exists
    dept = db.query(Department).filter(Department.id == employee.department_id).first()
    if not dept:
        raise HTTPException(status_code=404, detail=f"Department {employee.department_id} not found")

    db_employee = Employee(**employee.model_dump())
    db.add(db_employee)
    db.commit()
    db.refresh(db_employee)

    return EmployeeResponse.model_validate(db_employee)


@app.get(
    "/api/v1/employees/{employee_id}",
    response_model=EmployeeResponse,
    tags=["Employees"],
    summary="Get Employee",
    description="Get a single employee by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
    },
)
async def get_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")
    return EmployeeResponse.model_validate(employee)


@app.put(
    "/api/v1/employees/{employee_id}",
    response_model=EmployeeResponse,
    tags=["Employees"],
    summary="Update Employee",
    description="Update an existing employee. Only provided fields will be updated.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee or department not found"},
        409: {"model": ErrorResponse, "description": "Email already exists"},
    },
)
async def update_employee(
    employee_id: int,
    updates: EmployeeUpdate,
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    update_data = updates.model_dump(exclude_unset=True)

    # Validate department_id if provided
    if "department_id" in update_data:
        dept = db.query(Department).filter(Department.id == update_data["department_id"]).first()
        if not dept:
            raise HTTPException(
                status_code=404,
                detail=f"Department {update_data['department_id']} not found",
            )

    # Validate email uniqueness if provided
    if "email" in update_data:
        existing = (
            db.query(Employee)
            .filter(Employee.email == update_data["email"], Employee.id != employee_id)
            .first()
        )
        if existing:
            raise HTTPException(
                status_code=409,
                detail=f"Email {update_data['email']} already exists",
            )

    for field, value in update_data.items():
        setattr(employee, field, value)

    db.commit()
    db.refresh(employee)

    return EmployeeResponse.model_validate(employee)


@app.delete(
    "/api/v1/employees/{employee_id}",
    status_code=204,
    tags=["Employees"],
    summary="Delete Employee",
    description="Delete an employee by ID.",
    responses={
        404: {"model": ErrorResponse, "description": "Employee not found"},
    },
)
async def delete_employee(
    employee_id: int,
    db: Session = Depends(get_db),
):
    employee = db.query(Employee).filter(Employee.id == employee_id).first()
    if not employee:
        raise HTTPException(status_code=404, detail=f"Employee {employee_id} not found")

    db.delete(employee)
    db.commit()


# --- Department Endpoints ---

@app.get(
    "/api/v1/departments",
    response_model=list[DepartmentResponse],
    tags=["Departments"],
    summary="List Departments",
    description="Get all departments with employee count.",
)
async def list_departments(db: Session = Depends(get_db)):
    departments = db.query(Department).all()
    return [DepartmentResponse.model_validate(dept) for dept in departments]
