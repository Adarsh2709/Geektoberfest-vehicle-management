"""Tests for vehicle next-service reminders (Issue #11).

Acceptance criteria verified:
- User can set next-service date or mileage threshold
- Overdue, due, upcoming, and not-yet-due status calculations
- Safe handling of missing / None odometer readings
- Strict owner scoping (404 for non-owners)
- Status-based filtering in list_reminders
"""

from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import MaintenanceRecord, User, Vehicle


@pytest.fixture()
def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    db = Session()
    owner = User(username="owner", email="owner@example.com", hashed_password="x")
    stranger = User(username="stranger", email="stranger@example.com", hashed_password="x")
    db.add_all([owner, stranger])
    db.commit()
    db.refresh(owner)
    db.refresh(stranger)

    vehicle = Vehicle(
        make="Hyundai",
        model="Creta",
        year=2022,
        registration_number="KA01AA1111",
        current_mileage=15000,
        owner_id=owner.id,
    )
    stranger_vehicle = Vehicle(
        make="Honda",
        model="City",
        year=2021,
        registration_number="KA02BB2222",
        current_mileage=20000,
        owner_id=stranger.id,
    )
    db.add_all([vehicle, stranger_vehicle])
    db.commit()
    db.refresh(vehicle)
    db.refresh(stranger_vehicle)

    return {
        "db": db,
        "owner": owner,
        "stranger": stranger,
        "vehicle": vehicle,
        "stranger_vehicle": stranger_vehicle,
    }


def make_client(user: User, db):
    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_db] = lambda: db
    return TestClient(app)


def teardown_function():
    app.dependency_overrides.clear()


def test_set_and_get_reminder_threshold(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    target_date = (date.today() + timedelta(days=60)).isoformat()

    response = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": target_date, "next_service_mileage": 20000},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["next_service_date"] == target_date
    assert data["next_service_mileage"] == 20000
    assert data["km_remaining"] == 5000
    assert data["status"] == "not-yet-due"

    # Fetching the reminder via GET
    get_res = client.get(f"/vehicles/{v_id}/reminders")
    assert get_res.status_code == 200
    assert get_res.json()["next_service_mileage"] == 20000


def test_reminder_status_overdue_date(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    past_date = (date.today() - timedelta(days=5)).isoformat()

    res = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": past_date, "next_service_mileage": None},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date_status"] == "overdue"
    assert data["status"] == "overdue"
    assert data["days_remaining"] == -5


def test_reminder_status_overdue_mileage(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    # Current mileage is 15000, set threshold to 14500
    res = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": None, "next_service_mileage": 14500},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["mileage_status"] == "overdue"
    assert data["status"] == "overdue"
    assert data["km_remaining"] == -500


def test_reminder_status_due_date_and_mileage(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    today = date.today().isoformat()

    res = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": today, "next_service_mileage": 15000},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date_status"] == "due"
    assert data["mileage_status"] == "due"
    assert data["status"] == "due"
    assert data["days_remaining"] == 0
    assert data["km_remaining"] == 0


def test_reminder_status_upcoming(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    upcoming_date = (date.today() + timedelta(days=15)).isoformat()

    # Within 30 days and within 1000 km
    res = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": upcoming_date, "next_service_mileage": 15500},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date_status"] == "upcoming"
    assert data["mileage_status"] == "upcoming"
    assert data["status"] == "upcoming"
    assert data["days_remaining"] == 15
    assert data["km_remaining"] == 500


def test_reminder_status_not_yet_due(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    far_date = (date.today() + timedelta(days=90)).isoformat()

    res = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": far_date, "next_service_mileage": 25000},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["date_status"] == "not-yet-due"
    assert data["mileage_status"] == "not-yet-due"
    assert data["status"] == "not-yet-due"


def test_reminder_missing_odometer_handled_safely(setup):
    db = setup["db"]
    vehicle = setup["vehicle"]
    vehicle.current_mileage = None
    db.commit()

    client = make_client(setup["owner"], db)
    upcoming_date = (date.today() + timedelta(days=10)).isoformat()

    res = client.put(
        f"/vehicles/{vehicle.id}/reminders",
        json={"next_service_date": upcoming_date, "next_service_mileage": 20000},
    )
    assert res.status_code == 200
    data = res.json()
    # Missing odometer does not crash; mileage status is None while date status is calculated
    assert data["current_mileage"] is None
    assert data["mileage_status"] is None
    assert data["km_remaining"] is None
    assert data["date_status"] == "upcoming"
    assert data["status"] == "upcoming"


def test_reminders_scoped_to_vehicle_owner(setup):
    client = make_client(setup["stranger"], setup["db"])
    v_id = setup["vehicle"].id  # Belongs to owner

    # Stranger cannot view or edit owner's vehicle reminder
    res_get = client.get(f"/vehicles/{v_id}/reminders")
    assert res_get.status_code == 404

    res_put = client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": date.today().isoformat()},
    )
    assert res_put.status_code == 404


def test_list_reminders_and_status_filtering(setup):
    client = make_client(setup["owner"], setup["db"])
    v_id = setup["vehicle"].id
    past_date = (date.today() - timedelta(days=2)).isoformat()

    client.put(
        f"/vehicles/{v_id}/reminders",
        json={"next_service_date": past_date},
    )

    # All reminders for owner
    list_res = client.get("/vehicles/reminders")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) == 1
    assert items[0]["vehicle_id"] == v_id
    assert items[0]["status"] == "overdue"

    # Filter by overdue
    filter_overdue = client.get("/vehicles/reminders?status=overdue")
    assert filter_overdue.status_code == 200
    assert len(filter_overdue.json()) == 1

    # Filter by upcoming (should be 0)
    filter_upcoming = client.get("/vehicles/reminders?status=upcoming")
    assert filter_upcoming.status_code == 200
    assert len(filter_upcoming.json()) == 0
