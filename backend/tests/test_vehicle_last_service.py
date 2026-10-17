"""Tests for the last service date shown on vehicle cards.

Run from backend/: pytest -q
"""

from datetime import date

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
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()
    owner = User(username="owner", email="owner@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    db.refresh(owner)
    serviced = Vehicle(make="Maruti", model="Swift", year=2020, registration_number="KA01AB1234", current_mileage=50000, owner_id=owner.id)
    unserviced = Vehicle(make="Honda", model="City", year=2021, registration_number="MH02CD5678", current_mileage=10000, owner_id=owner.id)
    db.add_all([serviced, unserviced])
    db.commit()
    db.refresh(serviced)
    db.refresh(unserviced)
    # Inserted out of date order on purpose, so the test checks the latest date is picked.
    db.add_all([
        MaintenanceRecord(vehicle_id=serviced.id, service_date=date(2024, 1, 10), mileage=40000, service_type="Oil Change", cost=10),
        MaintenanceRecord(vehicle_id=serviced.id, service_date=date(2025, 3, 2), mileage=48000, service_type="Brake Service", cost=20),
        MaintenanceRecord(vehicle_id=serviced.id, service_date=date(2024, 8, 15), mileage=44000, service_type="Tire Change", cost=30),
    ])
    db.commit()
    owner_id = owner.id
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    class StubUser:
        id = owner_id

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: StubUser()
    yield
    app.dependency_overrides.clear()


def _vehicle_by_registration(registration_number):
    vehicles = TestClient(app).get("/vehicles").json()
    return next(vehicle for vehicle in vehicles if vehicle["registration_number"] == registration_number)


def test_last_service_date_is_the_latest_record_date(setup):
    vehicle = _vehicle_by_registration("KA01AB1234")

    assert vehicle["last_service_date"] == "2025-03-02"


def test_last_service_date_is_null_when_no_records(setup):
    vehicle = _vehicle_by_registration("MH02CD5678")

    assert vehicle["last_service_date"] is None
