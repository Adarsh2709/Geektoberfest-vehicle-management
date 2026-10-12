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
def setup_date_filter():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    db = Session()
    owner = User(username="driver", email="driver@test.com", hashed_password="pw")
    db.add(owner)
    db.commit()

    vehicle = Vehicle(
        make="Hyundai", model="i20", year=2022,
        registration_number="KA05ZZ1234", current_mileage=35000, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()

    # Three records on different dates: 2025-02-01, 2025-05-15, 2025-09-30
    r1 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 2, 1),
        mileage=10000, service_type="Oil Change", cost=Decimal("1200.00"),
    )
    r2 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 5, 15),
        mileage=20000, service_type="General Service", cost=Decimal("4500.00"),
    )
    r3 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 9, 30),
        mileage=30000, service_type="Brake Service", cost=Decimal("2500.00"),
    )
    db.add_all([r1, r2, r3])
    db.commit()

    v_id = vehicle.id
    u_id = owner.id
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    class StubUser:
        id = u_id

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: StubUser()
    client = TestClient(app)

    yield client, v_id
    app.dependency_overrides.clear()


def test_filter_exact_boundary_dates(setup_date_filter):
    client, v_id = setup_date_filter
    # Exactly from 2025-02-01 to 2025-05-15 (both inclusive)
    res = client.get(f"/vehicles/{v_id}/maintenance?start_date=2025-02-01&end_date=2025-05-15")
    assert res.status_code == 200
    dates = [r["service_date"] for r in res.json()]
    assert len(dates) == 2
    assert "2025-02-01" in dates
    assert "2025-05-15" in dates
    assert "2025-09-30" not in dates


def test_filter_start_date_only(setup_date_filter):
    client, v_id = setup_date_filter
    res = client.get(f"/vehicles/{v_id}/maintenance?start_date=2025-05-15")
    assert res.status_code == 200
    dates = [r["service_date"] for r in res.json()]
    assert len(dates) == 2
    assert "2025-05-15" in dates
    assert "2025-09-30" in dates


def test_filter_end_date_only(setup_date_filter):
    client, v_id = setup_date_filter
    res = client.get(f"/vehicles/{v_id}/maintenance?end_date=2025-05-15")
    assert res.status_code == 200
    dates = [r["service_date"] for r in res.json()]
    assert len(dates) == 2
    assert "2025-02-01" in dates
    assert "2025-05-15" in dates


def test_invalid_date_range_rejected(setup_date_filter):
    client, v_id = setup_date_filter
    # start_date after end_date must be rejected with 422
    res = client.get(f"/vehicles/{v_id}/maintenance?start_date=2025-09-01&end_date=2025-05-01")
    assert res.status_code == 422
    assert res.json()["detail"] == "start_date cannot be after end_date"


def test_filter_date_range_empty_result(setup_date_filter):
    client, v_id = setup_date_filter
    res = client.get(f"/vehicles/{v_id}/maintenance?start_date=2025-06-01&end_date=2025-08-01")
    assert res.status_code == 200
    assert res.json() == []
