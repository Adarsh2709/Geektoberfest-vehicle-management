from datetime import date
from pathlib import Path
from uuid import uuid4
import csv
import io

from fastapi import APIRouter, Depends, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import MaintenanceRecord, User, Vehicle
from app.schemas import MaintenanceCreate, MaintenanceRead, MaintenanceSummary, MaintenanceUpdate, SERVICE_TYPES

router = APIRouter(tags=["maintenance"])

ALLOWED_RECEIPT_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png", ".webp"}
ALLOWED_RECEIPT_CONTENT_TYPES = {"application/pdf", "image/jpeg", "image/png", "image/webp"}


def receipt_directory() -> Path:
    directory = Path(settings.receipt_dir)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def remove_receipt_file(path_value: str | None) -> None:
    if not path_value:
        return
    try:
        Path(path_value).unlink(missing_ok=True)
    except OSError:
        pass


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


def check_mileage(
    db: Session,
    vehicle_id: int,
    mileage: int,
    service_date: date | None = None,
    exclude_id: int | None = None,
    next_service_mileage: int | None = None,
) -> None:
    if mileage < 0:
        raise HTTPException(status_code=422, detail="Mileage must be a non-negative value")

    if next_service_mileage is not None and next_service_mileage < mileage:
        raise HTTPException(
            status_code=422,
            detail=f"Next service mileage ({next_service_mileage} km) cannot be lower than the current service mileage ({mileage} km)",
        )

    if service_date is not None:
        prev_q = select(func.max(MaintenanceRecord.mileage)).where(
            MaintenanceRecord.vehicle_id == vehicle_id,
            MaintenanceRecord.service_date < service_date,
        )
        if exclude_id is not None:
            prev_q = prev_q.where(MaintenanceRecord.id != exclude_id)
        prev_max = db.scalar(prev_q)

        same_day_q = select(func.min(MaintenanceRecord.mileage)).where(
            MaintenanceRecord.vehicle_id == vehicle_id,
            MaintenanceRecord.service_date == service_date,
        )
        if exclude_id is not None:
            same_day_q = same_day_q.where(MaintenanceRecord.id != exclude_id)
        same_day_min = db.scalar(same_day_q)

        lower_bound = prev_max
        if same_day_min is not None:
            lower_bound = max(prev_max, same_day_min) if prev_max is not None else same_day_min

        if lower_bound is not None and mileage < lower_bound:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Mileage {mileage} km is lower than the previous recorded reading {lower_bound} km. "
                    f"Correct the earlier entry, or enter a reading of at least {lower_bound} km."
                ),
            )

        next_q = select(func.min(MaintenanceRecord.mileage)).where(
            MaintenanceRecord.vehicle_id == vehicle_id,
            MaintenanceRecord.service_date > service_date,
        )
        if exclude_id is not None:
            next_q = next_q.where(MaintenanceRecord.id != exclude_id)
        next_min = db.scalar(next_q)
        if next_min is not None and mileage > next_min:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Mileage {mileage} km is higher than the subsequent recorded reading {next_min} km. "
                    f"Correct the later entry, or enter a reading of at most {next_min} km."
                ),
            )
    else:
        query = select(func.max(MaintenanceRecord.mileage)).where(MaintenanceRecord.vehicle_id == vehicle_id)
        if exclude_id is not None:
            query = query.where(MaintenanceRecord.id != exclude_id)
        highest = db.scalar(query)
        if highest is not None and mileage < highest:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Mileage {mileage} km is lower than the highest recorded reading {highest} km. "
                    f"Correct the earlier entry, or enter a reading of at least {highest} km."
                ),
            )


@router.post("/vehicles/{vehicle_id}/maintenance", response_model=MaintenanceRead, status_code=status.HTTP_201_CREATED)
def create_record(vehicle_id: int, data: MaintenanceCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    vehicle = owned_vehicle(db, vehicle_id, user.id)
    check_mileage(
        db,
        vehicle_id,
        data.mileage,
        service_date=data.service_date,
        next_service_mileage=data.next_service_mileage,
    )
    record = MaintenanceRecord(**data.model_dump(), vehicle_id=vehicle_id)
    db.add(record)
    if data.mileage > vehicle.current_mileage:
        vehicle.current_mileage = data.mileage
    db.commit()
    db.refresh(record)
    return record


@router.get("/vehicles/{vehicle_id}/maintenance/summary", response_model=MaintenanceSummary)
def maintenance_summary(
    vehicle_id: int, service_type: str | None = None,
    start_date: date | None = Query(default=None), end_date: date | None = Query(default=None),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date cannot be after end_date")
    owned_vehicle(db, vehicle_id, user.id)
    filters = [MaintenanceRecord.vehicle_id == vehicle_id]
    if service_type:
        filters.append(MaintenanceRecord.service_type == service_type)
    if start_date:
        filters.append(MaintenanceRecord.service_date >= start_date)
    if end_date:
        filters.append(MaintenanceRecord.service_date <= end_date)
    record_count, total_cost = db.execute(
        select(func.count(), func.coalesce(func.sum(func.coalesce(MaintenanceRecord.cost, 0)), 0)).where(*filters)
    ).one()
    return {
        "vehicle_id": vehicle_id, "record_count": record_count, "total_cost": total_cost,
        "start_date": start_date, "end_date": end_date, "service_type": service_type,
    }


@router.get("/vehicles/{vehicle_id}/maintenance", response_model=list[MaintenanceRead])
def list_records(
    vehicle_id: int, service_type: str | None = None,
    start_date: date | None = Query(default=None), end_date: date | None = Query(default=None),
    sort: str = Query(default="desc", pattern="^(asc|desc|date_asc|date_desc|cost_asc|cost_desc)$"),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=10, ge=1, le=100),
    db: Session = Depends(get_db), user: User = Depends(get_current_user),
):
    if service_type is not None and service_type not in SERVICE_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Unknown service type. Choose one of: {', '.join(sorted(SERVICE_TYPES))}",
        )
    owned_vehicle(db, vehicle_id, user.id)
    query = select(MaintenanceRecord).where(MaintenanceRecord.vehicle_id == vehicle_id)
    if service_type:
        query = query.where(MaintenanceRecord.service_type == service_type)
    if start_date:
        query = query.where(MaintenanceRecord.service_date >= start_date)
    if end_date:
        query = query.where(MaintenanceRecord.service_date <= end_date)
    if sort == "cost_desc":
        ordering = MaintenanceRecord.cost.desc().nulls_last()
    elif sort == "cost_asc":
        ordering = MaintenanceRecord.cost.asc().nulls_last()
    elif sort in ("asc", "date_asc"):
        ordering = MaintenanceRecord.service_date.asc().nulls_last()
    else:
        ordering = MaintenanceRecord.service_date.desc().nulls_last()
    query = query.order_by(ordering, MaintenanceRecord.id.desc())

    # Apply pagination offset and limit
    offset = (page - 1) * limit
    query = query.offset(offset).limit(limit)

    return db.scalars(query).all()


@router.get("/vehicles/{vehicle_id}/maintenance.csv")
def export_records_csv(
    vehicle_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
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
    check_mileage(
        db,
        record.vehicle_id,
        data.mileage,
        service_date=data.service_date,
        exclude_id=record.id,
        next_service_mileage=data.next_service_mileage,
    )
    for key, value in data.model_dump().items():
        setattr(record, key, value)
    vehicle = db.scalar(select(Vehicle).where(Vehicle.id == record.vehicle_id))
    if vehicle and data.mileage > vehicle.current_mileage:
        vehicle.current_mileage = data.mileage
    db.commit()
    db.refresh(record)
    return record


@router.delete("/maintenance/{record_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_record(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    receipt_path = record.receipt_path
    db.delete(record)
    db.commit()
    remove_receipt_file(receipt_path)


@router.post("/maintenance/{record_id}/receipt", response_model=MaintenanceRead, status_code=status.HTTP_201_CREATED)
async def upload_receipt(record_id: int, file: UploadFile, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    original_name = (file.filename or "").strip()
    extension = Path(original_name).suffix.lower()
    if extension not in ALLOWED_RECEIPT_EXTENSIONS or (file.content_type or "").lower() not in ALLOWED_RECEIPT_CONTENT_TYPES:
        raise HTTPException(status_code=422, detail="Receipt must be a PDF, JPG, PNG, or WebP file")
    contents = await file.read()
    max_bytes = settings.max_receipt_mb * 1024 * 1024
    if not contents or len(contents) > max_bytes:
        raise HTTPException(
            status_code=413 if contents else 422,
            detail=f"Receipt must not be empty and must be under {settings.max_receipt_mb} MB",
        )
    stored_name = f"{record.id}_{uuid4().hex}{extension}"
    target = receipt_directory() / stored_name
    old_path = record.receipt_path
    try:
        target.write_bytes(contents)
    except OSError:
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="Could not store the receipt. Please try again.")
    record.receipt_path = str(target)
    record.receipt_content_type = (file.content_type or "").lower()
    record.receipt_size = len(contents)
    record.receipt_original_name = Path(original_name).name[:255]
    try:
        db.commit()
    except Exception:
        db.rollback()
        try:
            target.unlink(missing_ok=True)
        except OSError:
            pass
        raise HTTPException(status_code=500, detail="Could not store the receipt. Please try again.")
    db.refresh(record)
    if old_path and old_path != record.receipt_path:
        remove_receipt_file(old_path)
    return record


@router.get("/maintenance/{record_id}/receipt")
def download_receipt(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    if not record.receipt_path or not Path(record.receipt_path).is_file():
        raise HTTPException(status_code=404, detail="Receipt not found")
    return FileResponse(
        record.receipt_path,
        media_type=record.receipt_content_type or "application/octet-stream",
        filename=record.receipt_original_name or Path(record.receipt_path).name,
    )


@router.delete("/maintenance/{record_id}/receipt", status_code=status.HTTP_204_NO_CONTENT)
def delete_receipt(record_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    record = owned_record(db, record_id, user.id)
    if not record.receipt_path:
        raise HTTPException(status_code=404, detail="Receipt not found")
    old_path = record.receipt_path
    record.receipt_path = None
    record.receipt_content_type = None
    record.receipt_size = None
    record.receipt_original_name = None
    db.commit()
    remove_receipt_file(old_path)