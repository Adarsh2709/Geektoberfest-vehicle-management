"""Tests for odometer mileage validation on maintenance records.

Rule: mileage must be non-negative; a reading lower than the vehicle's
highest recorded reading is rejected with a correction message.
Equal (repeated) readings are allowed.

Run from backend/: pytest -q
"""

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import MaintenanceRecord, User, Vehicle


def _payload(mileage, service_date="2026-01-10"):
    return {
        "service_date": service_date, "mileage": mileage, "service_type": "Oil Change",
        "description": None, "cost": "10.00",
        "next_service_date": None, "next_service_mileage": None,
    }


@pytest.fixture()
def setup():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    db = Session()
    owner = User(username="owner", email="owner@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    vehicle = Vehicle(
        make="Maruti", model="Swift", year=2020,
        registration_number="KA01MM0001", current_mileage=0, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    db.add(MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2026, 1, 10),
        mileage=1000, service_type="Oil Change", cost=Decimal("10.00"),
    ))
    db.commit()
    ids = {"owner": owner.id, "vehicle": vehicle.id}
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    class StubUser:
        id = ids["owner"]

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: StubUser()
    yield ids
    app.dependency_overrides.clear()


def test_valid_increasing_reading_is_accepted(setup):
    response = TestClient(app).post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(1500, "2026-02-01")
    )
    assert response.status_code == 201
    assert response.json()["mileage"] == 1500


def test_repeated_reading_is_allowed(setup):
    response = TestClient(app).post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(1000, "2026-01-11")
    )
    assert response.status_code == 201


def test_decreasing_reading_is_rejected_with_correction_message(setup):
    client = TestClient(app)
    before = client.get(f"/vehicles/{setup['vehicle']}/maintenance").json()
    response = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(900, "2026-01-12")
    )
    assert response.status_code == 422
    assert "1000" in response.json()["detail"]
    assert "Correct the earlier entry" in response.json()["detail"]
    after = client.get(f"/vehicles/{setup['vehicle']}/maintenance").json()
    assert len(after) == len(before)


def test_corrected_reading_is_accepted(setup):
    client = TestClient(app)
    assert client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(900, "2026-01-12")
    ).status_code == 422
    response = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(1100, "2026-01-12")
    )
    assert response.status_code == 201


def test_negative_reading_is_rejected(setup):
    response = TestClient(app).post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(-5)
    )
    assert response.status_code == 422


def test_update_to_decreasing_reading_is_rejected(setup):
    client = TestClient(app)
    created = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(1500, "2026-03-01")
    ).json()
    response = client.put(f"/maintenance/{created['id']}", json=_payload(500, "2026-03-01"))
    assert response.status_code == 422
    assert "Correct the earlier entry" in response.json()["detail"]
    assert client.put(f"/maintenance/{created['id']}", json=_payload(1600, "2026-03-01")).status_code == 200
