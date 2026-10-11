from datetime import date

import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import MaintenanceRecord, User, Vehicle
from app.schemas import MaintenanceCreate, MaintenanceRead, MaintenanceUpdate

router = APIRouter(tags=["maintenance"])

# Columns written by the CSV export, in order.
CSV_COLUMNS = [
    "id",
    "service_date",
    "mileage",
    "service_type",
    "description",
    "cost",
    "next_service_date",
    "next_service_mileage",
]


def owned_vehicle(db: Session, vehicle_id: int, owner_id: int) -> Vehicle:
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == vehicle_id, Vehicle.owner_id == owner_id))
    if vehicle is None:
        raise HTTPException(status_code=404, detail="Vehicle not found")
    return vehicle


def owned_record(db: Session, record_id: int, owner_id: int) -> MaintenanceRecord:
    record = db.scalar(select(MaintenanceRecord).join(Vehicle).where(MaintenanceRecord.id == record_id, Vehicle.owner_id == owner_id))
    if record is None:
        raise HTTPException(status_code=404, detail="Maintenance record not found")
    return record


@router.post("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceRead, status_code=status.HTTP_201_CREATED)
def create_record(vehicle_id: int, data: MaintenanceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    owned_vehicle(db, vehicle_id, user.id)
    record = MaintenanceRecord(**data.model_dump(), vehicle_id=vehicle_id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.get("/vehicles/{vehicle_id}/maintenance", response_model=list[MaintenanceRead])
def list_records(
    vehicle_id: int, service_type: str | None = None,
    start_date: date | None = Query(default=None), end_date: date | None = Query(default=None),
    sort: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    owned_vehicle(db, vehicle_id, user.id)
    query = select(MaintenanceRecord).where(MaintenanceRecord.vehicle_id == vehicle_id)
    if service_type:
        query = query.where(MaintenanceRecord.service_type == service_type)
    if start_date:
        query = query.where(MaintenanceRecord.service_date >= start_date)
    if end_date:
        query = query.where(MaintenanceRecord.service_date <= end_date)
    ordering = MaintenanceRecord.service_date.asc() if sort == "asc" else MaintenanceRecord.service_date.desc()
    return db.scalars(query.order_by(ordering, MaintenanceRecord.id.desc())).all()


@router.get("/vehicles/{vehicle_id}/maintenance.csv")
def export_records_csv(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Download the signed-in user's maintenance history for a vehicle as CSV.

    Only the vehicle owner may export, and only that vehicle's records are
    included. Columns are listed in ``CSV_COLUMNS``; values are written with the
    standard-library csv writer so commas, quotes, and line breaks in free-text
    fields (e.g. ``description``) are escaped correctly.
    """
    owned_vehicle(db, vehicle_id, user.id)
    records = db.scalars(
        select(MaintenanceRecord)
        .where(MaintenanceRecord.vehicle_id == vehicle_id)
        .order_by(MaintenanceRecord.service_date.desc(), MaintenanceRecord.id.desc())
    ).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for record in records:
        writer.writerow([
            record.id,
            record.service_date.isoformat() if record.service_date else "",
            record.mileage,
            record.service_type,
            record.description or "",
            record.cost if record.cost is not None else "",
            record.next_service_date.isoformat() if record.next_service_date else "",
            record.next_service_mileage if record.next_service_mileage is not None else "",
        ])

    filename = f"vehicle-{vehicle_id}-maintenance.csv"
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/maintenance/{record_id}", response_model=MaintenanceRead)
def get_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    return owned_record(db, record_id, user.id)


@router.put("/maintenance/{record_id}", response_model=MaintenanceRead)
def update_record(record_id: int, data: MaintenanceUpdate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    db.commit()
    db.refresh(record)
    return record


@router.delete("/maintenance/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    db.delete(record)
    db.commit()
