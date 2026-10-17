import os

os.environ["DATABASE_URL"] = "sqlite+pysqlite:///:memory:"
os.environ.setdefault("SECRET_KEY", "test-secret")

import csv
import io
from datetime import date
from decimal import Decimal

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.models import MaintenanceRecord, User, Vehicle
from app.routes import maintenance as maintenance_module

engine = create_engine(
    "sqlite+pysqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestSession = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

_CURRENT = {"user": None}


def _override_get_db():
    db = TestSession()
    try:
        yield db
    finally:
        db.close()


app = FastAPI()
app.include_router(maintenance_module.router)
app.dependency_overrides[get_db] = _override_get_db
app.dependency_overrides[get_current_user] = lambda: _CURRENT["user"]
client = TestClient(app)


@pytest.fixture(autouse=True)
def fresh_db():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    _CURRENT["user"] = None
    yield


def _user(user_id):
    db = TestSession()
    user = db.get(User, user_id)
    db.close()
    return user


def _seed_vehicle_with_records():
    db = TestSession()
    owner = User(username="owner", email="owner@ex.com", hashed_password="x")
    other = User(username="other", email="other@ex.com", hashed_password="x")
    db.add_all([owner, other])
    db.flush()

    vehicle = Vehicle(
        make="Toyota", model="Corolla", year=2020,
        registration_number="REG-1", current_mileage=50000, owner_id=owner.id,
    )
    db.add(vehicle)
    db.flush()

    db.add_all([
        MaintenanceRecord(
            vehicle_id=vehicle.id, service_date=date(2024, 1, 10), mileage=40000,
            service_type="Oil change", description="Routine", cost=Decimal("49.99"),
        ),
        MaintenanceRecord(
            vehicle_id=vehicle.id, service_date=date(2024, 6, 20), mileage=45000,
            # Free text with a comma, a quote, and a newline to exercise escaping.
            service_type="Brake service",
            description='Replaced pads, rotors; note: "worn", check\nnext visit',
            cost=Decimal("220.00"), next_service_date=date(2025, 6, 20), next_service_mileage=55000,
        ),
    ])
    db.commit()
    ids = {"vehicle": vehicle.id, "owner": owner.id, "other": other.id}
    db.close()
    return ids


def test_owner_exports_history_as_csv_sorted_desc():
    ids = _seed_vehicle_with_records()
    _CURRENT["user"] = _user(ids["owner"])

    resp = client.get(f"/vehicles/{ids['vehicle']}/maintenance.csv")

    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/csv")
    assert "attachment" in resp.headers["content-disposition"]
    assert f"vehicle-{ids['vehicle']}-maintenance.csv" in resp.headers["content-disposition"]

    rows = list(csv.reader(io.StringIO(resp.text)))
    assert rows[0] == [
        "id", "service_date", "mileage", "service_type",
        "description", "cost", "next_service_date", "next_service_mileage",
    ]
    # Newest service_date first.
    assert rows[1][1] == "2024-06-20"
    assert rows[2][1] == "2024-01-10"
    assert len(rows) == 3


def test_csv_escapes_special_characters_in_free_text():
    ids = _seed_vehicle_with_records()
    _CURRENT["user"] = _user(ids["owner"])

    resp = client.get(f"/vehicles/{ids['vehicle']}/maintenance.csv")
    rows = list(csv.reader(io.StringIO(resp.text)))

    # The brake-service row is first (newest). Its description round-trips with
    # the embedded comma, quote, and newline intact after CSV parsing.
    brake_row = rows[1]
    assert brake_row[3] == "Brake service"
    assert brake_row[4] == 'Replaced pads, rotors; note: "worn", check\nnext visit'


def test_non_owner_cannot_export():
    ids = _seed_vehicle_with_records()
    _CURRENT["user"] = _user(ids["other"])

    resp = client.get(f"/vehicles/{ids['vehicle']}/maintenance.csv")
    assert resp.status_code == 404


def test_export_includes_only_selected_vehicle_records():
    ids = _seed_vehicle_with_records()
    db = TestSession()
    other_vehicle = Vehicle(
        make="Honda", model="Civic", year=2022,
        registration_number="REG-3", current_mileage=1000, owner_id=ids["owner"],
    )
    db.add(other_vehicle)
    db.flush()
    db.add(MaintenanceRecord(
        vehicle_id=other_vehicle.id, service_date=date(2024, 3, 1), mileage=900,
        service_type="Battery", description="Other vehicle only", cost=Decimal("10.00"),
    ))
    db.commit()
    db.close()
    _CURRENT["user"] = _user(ids["owner"])

    resp = client.get(f"/vehicles/{ids['vehicle']}/maintenance.csv")
    rows = list(csv.reader(io.StringIO(resp.text)))

    assert len(rows) == 3
    assert all("Other vehicle only" not in row for row in rows)


def test_empty_history_returns_header_only():
    db = TestSession()
    owner = User(username="solo", email="solo@ex.com", hashed_password="x")
    db.add(owner)
    db.flush()
    vehicle = Vehicle(
        make="Honda", model="Civic", year=2022,
        registration_number="REG-2", current_mileage=10, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()
    vehicle_id, owner_id = vehicle.id, owner.id
    db.close()

    _CURRENT["user"] = _user(owner_id)
    resp = client.get(f"/vehicles/{vehicle_id}/maintenance.csv")
    assert resp.status_code == 200
    assert resp.text.strip() == "id,service_date,mileage,service_type,description,cost,next_service_date,next_service_mileage"
