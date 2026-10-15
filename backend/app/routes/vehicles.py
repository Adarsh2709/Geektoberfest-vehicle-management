from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Vehicle
from app.schemas import VehicleCreate, VehicleRead, VehicleUpdate

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def owned_vehicle(db: Session, vehicle_id: int, owner_id: int) -> Vehicle:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == owner_id))
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def dashboard_vehicle(vehicle: Vehicle) -> dict:
    records = list(vehicle.maintenance_records or [])
    latest = max(records, key=lambda r: (r.service_date, r.id or 0)) if records else None
    upcoming = [record.next_service_date for record in records if record.next_service_date and record.next_service_date >= date.today()]
    return {
        "id": vehicle.id, "make": vehicle.make, "model": vehicle.model, "year": vehicle.year,
        "registration_number": vehicle.registration_number, "current_mileage": vehicle.current_mileage,
        "owner_id": vehicle.owner_id, "created_at": vehicle.created_at, "maintenance_count": len(records),
        "last_service_date": latest.service_date if latest else None,
        "next_service_date": min(upcoming) if upcoming else (latest.next_service_date if latest else None),
    }


@router.post("", response_model=VehicleRead, status_code=status.HTTP_201_CREATED)
def create_vehicle(data: VehicleCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = Vehicle(**data.model_dump(), owner_id=user.id)
    db.add(vehicle)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That registration number is already in use")
    db.refresh(vehicle)
    return dashboard_vehicle(vehicle)


@router.get("", response_model=list[VehicleRead])
def list_vehicles(
    registration_number: str | None = Query(default=None, max_length=30),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = select(Vehicle).options(selectinload(Vehicle.maintenance_records)).where(Vehicle.owner_id == user.id)
    search = registration_number.strip() if registration_number else ""
    if search:
        statement = statement.where(func.lower(Vehicle.registration_number).contains(search.lower(), autoescape=True))
    vehicles = db.scalars(statement.order_by(Vehicle.created_at.desc())).all()
    return [dashboard_vehicle(vehicle) for vehicle in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleRead)
def get_vehicle(vehicle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = db.scalar(select(Vehicle).options(selectinload(Vehicle.maintenance_records)).where(Vehicle.id == vehicle_id, Vehicle.owner_id == user.id))
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return dashboard_vehicle(vehicle)


@router.put("/{vehicle_id}", response_model=VehicleRead)
def update_vehicle(vehicle_id: int, data: VehicleUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = owned_vehicle(db, vehicle_id, user.id)
    for key, value in data.model_dump().items():
        setattr(vehicle, key, value)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="That registration number is already in use")
    db.refresh(vehicle)
    return dashboard_vehicle(vehicle)


@router.delete("/{vehicle_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_vehicle(vehicle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = owned_vehicle(db, vehicle_id, user.id)
    db.delete(vehicle)
    db.commit()
