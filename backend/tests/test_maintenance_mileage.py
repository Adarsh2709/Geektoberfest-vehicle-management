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


def test_valid_intermediate_date_reading_is_accepted(setup):
    client = TestClient(app)
    # Existing record is 1000 km on 2026-01-10
    # Add a future record on 2026-03-10 with 3000 km
    res_future = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(3000, "2026-03-10")
    )
    assert res_future.status_code == 201

    # Insert an intermediate record on 2026-02-10 with 2000 km (between 1000 and 3000)
    res_mid = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(2000, "2026-02-10")
    )
    assert res_mid.status_code == 201
    assert res_mid.json()["mileage"] == 2000


def test_intermediate_reading_higher_than_subsequent_is_rejected(setup):
    client = TestClient(app)
    # Existing record is 1000 km on 2026-01-10
    # Add a future record on 2026-03-10 with 3000 km
    client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(3000, "2026-03-10")
    )

    # Attempt to insert an intermediate record on 2026-02-10 with 3500 km (> 3000 km)
    response = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(3500, "2026-02-10")
    )
    assert response.status_code == 422
    assert "higher than the subsequent recorded reading" in response.json()["detail"]


def test_update_earlier_record_higher_than_subsequent_is_rejected(setup):
    client = TestClient(app)
    # Existing record is 1000 km on 2026-01-10
    res_future = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(3000, "2026-03-10")
    )
    assert res_future.status_code == 201

    # Get the 2026-01-10 record ID
    records = client.get(f"/vehicles/{setup['vehicle']}/maintenance").json()
    earlier_rec = [r for r in records if r["service_date"] == "2026-01-10"][0]

    # Attempt to update the earlier record to 4000 km (> 3000 km of subsequent record)
    response = client.put(f"/maintenance/{earlier_rec['id']}", json=_payload(4000, "2026-01-10"))
    assert response.status_code == 422
    assert "higher than the subsequent recorded reading" in response.json()["detail"]


def test_next_service_mileage_lower_than_current_is_rejected(setup):
    client = TestClient(app)
    payload = _payload(1500, "2026-02-01")
    payload["next_service_mileage"] = 1200
    response = client.post(f"/vehicles/{setup['vehicle']}/maintenance", json=payload)
    assert response.status_code == 422
    assert "cannot be lower" in response.json()["detail"]


def test_vehicle_current_mileage_syncs_with_highest_service_reading(setup):
    client = TestClient(app)
    # Post a service reading of 2500 km
    response = client.post(
        f"/vehicles/{setup['vehicle']}/maintenance", json=_payload(2500, "2026-04-01")
    )
    assert response.status_code == 201

    # Vehicle current_mileage should now be 2500 km
    veh_response = client.get(f"/vehicles/{setup['vehicle']}")
    assert veh_response.status_code == 200
    assert veh_response.json()["current_mileage"] == 2500
