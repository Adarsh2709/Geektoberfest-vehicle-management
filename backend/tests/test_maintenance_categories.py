"""Tests for maintenance record category validation.

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
from app.schemas import SERVICE_TYPES


def _payload(service_type, **overrides):
    data = {
        "service_date": "2026-01-10", "mileage": 100, "service_type": service_type,
        "description": None, "cost": "10.00",
        "next_service_date": None, "next_service_mileage": None,
    }
    data.update(overrides)
    return data


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
        registration_number="KA09CT0001", current_mileage=0, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
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
    yield {"ids": ids, "Session": Session}
    app.dependency_overrides.clear()


def test_all_known_categories_are_accepted(setup):
    client = TestClient(app)
    assert SERVICE_TYPES == {
        "Oil Change", "General Service", "Brake Service",
        "Tire Change", "Battery", "Other",
    }
    for service_type in sorted(SERVICE_TYPES):
        response = client.post(
            f"/vehicles/{setup['ids']['vehicle']}/maintenance", json=_payload(service_type)
        )
        assert response.status_code == 201
        assert response.json()["service_type"] == service_type


def test_unknown_category_is_rejected_on_create(setup):
    client = TestClient(app)
    before = client.get(f"/vehicles/{setup['ids']['vehicle']}/maintenance").json()
    response = client.post(
        f"/vehicles/{setup['ids']['vehicle']}/maintenance", json=_payload("Warp Drive")
    )
    assert response.status_code == 422
    assert "Unknown service type" in str(response.json())
    after = client.get(f"/vehicles/{setup['ids']['vehicle']}/maintenance").json()
    assert after == before


def test_unknown_category_is_rejected_on_update(setup):
    client = TestClient(app)
    record_id = client.post(
        f"/vehicles/{setup['ids']['vehicle']}/maintenance", json=_payload("Oil Change")
    ).json()["id"]
    response = client.put(f"/maintenance/{record_id}", json=_payload("Warp Drive"))
    assert response.status_code == 422
    assert client.get(f"/maintenance/{record_id}").json()["service_type"] == "Oil Change"


def test_unknown_category_filter_is_rejected(setup):
    client = TestClient(app)
    assert client.get(
        f"/vehicles/{setup['ids']['vehicle']}/maintenance",
        params={"service_type": "Warp Drive"},
    ).status_code == 422
    assert client.get(
        f"/vehicles/{setup['ids']['vehicle']}/maintenance",
        params={"service_type": "Oil Change"},
    ).status_code == 200


def test_legacy_free_text_record_stays_readable(setup):
    # Simulate a pre-validation row written directly to the database.
    db = setup["Session"]()
    db.add(MaintenanceRecord(
        vehicle_id=setup["ids"]["vehicle"], service_date=date(2025, 12, 1),
        mileage=50, service_type="oil change", cost=Decimal("5.00"),
    ))
    db.commit()
    db.close()

    client = TestClient(app)
    records = client.get(f"/vehicles/{setup['ids']['vehicle']}/maintenance").json()
    assert any(record["service_type"] == "oil change" for record in records)
