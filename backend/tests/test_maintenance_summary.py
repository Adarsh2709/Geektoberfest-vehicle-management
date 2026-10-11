"""Tests for GET /vehicles/{vehicle_id}/maintenance/summary.

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
        make="Maruti", model="Swift", year=2020,
        registration_number="KA01AB1234", current_mileage=50000, owner_id=owner.id,
    )
    other_vehicle = Vehicle(
        make="Honda", model="City", year=2021,
        registration_number="KA02CD5678", current_mileage=10000, owner_id=stranger.id,
    )
    db.add_all([vehicle, other_vehicle])
    db.commit()
    db.refresh(vehicle)
    db.refresh(other_vehicle)

    db.add_all([
        MaintenanceRecord(
            vehicle_id=vehicle.id, service_date=date(2026, 1, 10),
            mileage=1000, service_type="Oil Change", cost=Decimal("100.50"),
        ),
        MaintenanceRecord(
            vehicle_id=vehicle.id, service_date=date(2026, 2, 15),
            mileage=2000, service_type="Brake Service", cost=Decimal("200.00"),
        ),
        MaintenanceRecord(
            vehicle_id=vehicle.id, service_date=date(2026, 3, 20),
            mileage=3000, service_type="Oil Change", cost=Decimal("300.25"),
        ),
    ])
    db.commit()
    ids = {"owner": owner.id, "vehicle": vehicle.id, "other_vehicle": other_vehicle.id}
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


def test_total_without_filters(setup):
    response = TestClient(app).get(f"/vehicles/{setup['vehicle']}/maintenance/summary")
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 3
    assert Decimal(body["total_cost"]) == Decimal("600.75")


def test_total_for_date_range(setup):
    response = TestClient(app).get(
        f"/vehicles/{setup['vehicle']}/maintenance/summary",
        params={"start_date": "2026-02-01", "end_date": "2026-03-01"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 1
    assert Decimal(body["total_cost"]) == Decimal("200.00")


def test_date_boundaries_are_inclusive(setup):
    client = TestClient(app)
    response = client.get(
        f"/vehicles/{setup['vehicle']}/maintenance/summary",
        params={"start_date": "2026-02-15", "end_date": "2026-02-15"},
    )
    assert response.status_code == 200
    assert response.json()["record_count"] == 1

    response = client.get(
        f"/vehicles/{setup['vehicle']}/maintenance/summary",
        params={"start_date": "2026-01-10", "end_date": "2026-03-20"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 3
    assert Decimal(body["total_cost"]) == Decimal("600.75")


def test_empty_range_returns_zero(setup):
    response = TestClient(app).get(
        f"/vehicles/{setup['vehicle']}/maintenance/summary",
        params={"start_date": "2027-01-01", "end_date": "2027-12-31"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["record_count"] == 0
    assert Decimal(body["total_cost"]) == Decimal("0")


def test_inverted_range_is_rejected(setup):
    response = TestClient(app).get(
        f"/vehicles/{setup['vehicle']}/maintenance/summary",
        params={"start_date": "2026-05-01", "end_date": "2026-01-01"},
    )
    assert response.status_code == 422


def test_other_owners_vehicle_is_not_found(setup):
    response = TestClient(app).get(
        f"/vehicles/{setup['other_vehicle']}/maintenance/summary"
    )
    assert response.status_code == 404
