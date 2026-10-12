from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class UserCreate(BaseModel):
    username: str = Field(min_length=2, max_length=50)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserRead(BaseModel):
    id: int
    username: str
    email: EmailStr
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class VehicleBase(BaseModel):
    make: str = Field(min_length=1, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=1886, le=2100)
    registration_number: str = Field(min_length=1, max_length=30)
    current_mileage: int = Field(ge=0)

    @field_validator("make", "model", "registration_number")
    @classmethod
    def not_blank(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("This field cannot be blank")
        return value


class VehicleCreate(VehicleBase):
    pass


class VehicleUpdate(VehicleBase):
    pass


SERVICE_TYPES = frozenset({
    "Oil Change",
    "General Service",
    "Brake Service",
    "Tire Change",
    "Battery",
    "Other",
})


def validate_service_type(value: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError("Service type cannot be blank")
    if value not in SERVICE_TYPES:
        raise ValueError(f"Unknown service type. Choose one of: {', '.join(sorted(SERVICE_TYPES))}")
    return value


class MaintenanceBase(BaseModel):
    service_date: date
    mileage: int = Field(ge=0)
    service_type: str = Field(min_length=1, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    cost: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    next_service_date: date | None = None
    next_service_mileage: int | None = Field(default=None, ge=0)

    @field_validator("service_type")
    @classmethod
    def service_type_must_be_known(cls, value: str) -> str:
        return validate_service_type(value)


class MaintenanceCreate(MaintenanceBase):
    pass


class MaintenanceUpdate(MaintenanceBase):
    pass


class MaintenanceRead(MaintenanceBase):
    id: int
    vehicle_id: int
    created_at: datetime
    receipt_original_name: str | None = None
    receipt_content_type: str | None = None
    receipt_size: int | None = None
    model_config = ConfigDict(from_attributes=True)


class MaintenanceSummary(BaseModel):
    vehicle_id: int
    record_count: int
    total_cost: Decimal
    start_date: date | None = None
    end_date: date | None = None
    service_type: str | None = None


class VehicleRead(VehicleBase):
    id: int
    owner_id: int
    created_at: datetime
    maintenance_count: int = 0
    last_service_date: date | None = None
    next_service_date: date | None = None
    model_config = ConfigDict(from_attributes=True)
