"""Pydantic models for request/response validation."""

from datetime import UTC, datetime
from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, EmailStr, Field


# --- Employee Models ---

class EmployeeBase(BaseModel):
    """Base employee fields."""
    first_name: str = Field(..., min_length=1, max_length=100, examples=["Eduardo"])
    last_name: str = Field(..., min_length=1, max_length=100, examples=["Tavares"])
    email: EmailStr = Field(..., examples=["eduardo@company.com"])
    department_id: int = Field(..., ge=1, examples=[1])
    position: str = Field(..., min_length=1, max_length=200, examples=["RPA Engineer"])
    salary: Decimal = Field(..., gt=0, decimal_places=2, examples=[10000.00])
    is_active: bool = Field(default=True)


class EmployeeCreate(EmployeeBase):
    """Schema for creating an employee."""
    pass


class EmployeeUpdate(BaseModel):
    """Schema for updating an employee (all fields optional)."""
    first_name: Optional[str] = Field(None, min_length=1, max_length=100)
    last_name: Optional[str] = Field(None, min_length=1, max_length=100)
    email: Optional[EmailStr] = None
    department_id: Optional[int] = Field(None, ge=1)
    position: Optional[str] = Field(None, min_length=1, max_length=200)
    salary: Optional[Decimal] = Field(None, gt=0, decimal_places=2)
    is_active: Optional[bool] = None


class EmployeeResponse(EmployeeBase):
    """Schema for employee response."""
    id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class EmployeeListResponse(BaseModel):
    """Paginated list of employees."""
    items: list[EmployeeResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# --- Department Models ---

class DepartmentBase(BaseModel):
    """Base department fields."""
    name: str = Field(..., min_length=1, max_length=100, examples=["Engineering"])
    code: str = Field(..., min_length=1, max_length=10, examples=["ENG"])


class DepartmentResponse(DepartmentBase):
    """Schema for department response."""
    id: int
    employee_count: int = 0

    model_config = {"from_attributes": True}


# --- Health Check ---

class HealthResponse(BaseModel):
    """Health check response."""
    status: str = "healthy"
    version: str = "1.0.0"
    timestamp: datetime


# --- Error Models ---

class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str
    status_code: int
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
