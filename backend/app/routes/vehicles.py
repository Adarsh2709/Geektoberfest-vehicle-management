from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.auth import get_current_user
from app.database import get_db
from app.models import User, Vehicle
from app.schemas import (
    ReminderThresholdUpdate,
    ServiceReminder,
    VehicleCreate,
    VehicleRead,
    VehicleUpdate,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def owned_vehicle(db: Session, vehicle_id: int, owner_id: int) -> Vehicle:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == owner_id))
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def compute_service_reminder(vehicle: Vehicle, today: date | None = None) -> ServiceReminder | None:
    if today is None:
        today = date.today()

    records = vehicle.maintenance_records or []
    latest = records[0] if records else None

    # Next service date priority: explicitly set on vehicle, or from records
    next_date = vehicle.next_service_date
    if next_date is None:
        upcoming_dates = [r.next_service_date for r in records if r.next_service_date and r.next_service_date >= today]
        next_date = min(upcoming_dates) if upcoming_dates else (latest.next_service_date if latest else None)

    # Next service mileage priority: explicitly set on vehicle, or latest record
    next_mileage = vehicle.next_service_mileage
    if next_mileage is None and latest and latest.next_service_mileage is not None:
        next_mileage = latest.next_service_mileage

    if next_date is None and next_mileage is None:
        return None

    date_status = None
    days_remaining = None
    if next_date is not None:
        days_remaining = (next_date - today).days
        if days_remaining < 0:
            date_status = "overdue"
        elif days_remaining == 0:
            date_status = "due"
        elif days_remaining <= 30:
            date_status = "upcoming"
        else:
            date_status = "not-yet-due"

    mileage_status = None
    km_remaining = None
    if next_mileage is not None and vehicle.current_mileage is not None:
        km_remaining = next_mileage - vehicle.current_mileage
        if km_remaining < 0:
            mileage_status = "overdue"
        elif km_remaining == 0:
            mileage_status = "due"
        elif km_remaining <= 1000:
            mileage_status = "upcoming"
        else:
            mileage_status = "not-yet-due"

    statuses = [s for s in (date_status, mileage_status) if s is not None]
    if "overdue" in statuses:
        overall = "overdue"
    elif "due" in statuses:
        overall = "due"
    elif "upcoming" in statuses:
        overall = "upcoming"
    elif "not-yet-due" in statuses:
        overall = "not-yet-due"
    else:
        overall = None

    return ServiceReminder(
        vehicle_id=vehicle.id,
        registration_number=vehicle.registration_number,
        make=vehicle.make,
        model=vehicle.model,
        current_mileage=vehicle.current_mileage,
        next_service_date=next_date,
        next_service_mileage=next_mileage,
        date_status=date_status,
        mileage_status=mileage_status,
        status=overall,
        days_remaining=days_remaining,
        km_remaining=km_remaining,
    )


def dashboard_vehicle(vehicle: Vehicle) -> dict:
    records = vehicle.maintenance_records or []
    latest = records[0] if records else None
    reminder = compute_service_reminder(vehicle)
    return {
        "id": vehicle.id,
        "make": vehicle.make,
        "model": vehicle.model,
        "year": vehicle.year,
        "registration_number": vehicle.registration_number,
        "current_mileage": vehicle.current_mileage,
        "owner_id": vehicle.owner_id,
        "created_at": vehicle.created_at,
        "maintenance_count": len(records),
        "last_service_date": latest.service_date if latest else None,
        "next_service_date": reminder.next_service_date if reminder else None,
        "next_service_mileage": reminder.next_service_mileage if reminder else None,
        "service_status": reminder.status if reminder else None,
        "service_reminder": reminder,
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


@router.get("/reminders", response_model=list[ServiceReminder])
def list_reminders(
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vehicles = db.scalars(
        select(Vehicle)
        .options(selectinload(Vehicle.maintenance_records))
        .where(Vehicle.owner_id == user.id)
    ).all()
    reminders = []
    for vehicle in vehicles:
        reminder = compute_service_reminder(vehicle)
        if reminder and reminder.status:
            if status_filter is None or reminder.status == status_filter:
                reminders.append(reminder)
    return reminders


@router.get("/{vehicle_id}/reminders", response_model=ServiceReminder)
def get_vehicle_reminder(vehicle_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = db.scalar(
        select(Vehicle)
        .options(selectinload(Vehicle.maintenance_records))
        .where(Vehicle.id == vehicle_id, Vehicle.owner_id == user.id)
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    reminder = compute_service_reminder(vehicle)
    if reminder is None:
        return ServiceReminder(
            vehicle_id=vehicle.id,
            registration_number=vehicle.registration_number,
            make=vehicle.make,
            model=vehicle.model,
            current_mileage=vehicle.current_mileage,
        )
    return reminder


@router.put("/{vehicle_id}/reminders", response_model=ServiceReminder)
def update_vehicle_reminder(
    vehicle_id: int,
    data: ReminderThresholdUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    vehicle = db.scalar(
        select(Vehicle)
        .options(selectinload(Vehicle.maintenance_records))
        .where(Vehicle.id == vehicle_id, Vehicle.owner_id == user.id)
    )
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    vehicle.next_service_date = data.next_service_date
    vehicle.next_service_mileage = data.next_service_mileage
    db.commit()
    db.refresh(vehicle)
    reminder = compute_service_reminder(vehicle)
    if reminder is None:
        return ServiceReminder(
            vehicle_id=vehicle.id,
            registration_number=vehicle.registration_number,
            make=vehicle.make,
            model=vehicle.model,
            current_mileage=vehicle.current_mileage,
        )
    return reminder


@router.get("", response_model=list[VehicleRead])
def list_vehicles(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicles = db.scalars(select(Vehicle).options(selectinload(Vehicle.maintenance_records)).where(Vehicle.owner_id == user.id).order_by(Vehicle.created_at.desc())).all()
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
