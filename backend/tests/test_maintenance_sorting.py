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
def setup_sorting():
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)

    db = Session()
    owner = User(username="car_owner", email="owner@test.com", hashed_password="pw")
    db.add(owner)
    db.commit()

    vehicle = Vehicle(
        make="Toyota", model="Corolla", year=2020,
        registration_number="MH02AB9999", current_mileage=50000, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()

    # Add records with different dates, costs, and one missing cost
    r1 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 1, 15),
        mileage=10000, service_type="Oil Change", cost=Decimal("1500.00"),
    )
    r2 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 6, 20),
        mileage=20000, service_type="Brake Service", cost=Decimal("5000.00"),
    )
    r3 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 11, 10),
        mileage=30000, service_type="General Service", cost=Decimal("3000.00"),
    )
    r4 = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2025, 3, 5),
        mileage=15000, service_type="Oil Change", cost=None,
    )
    db.add_all([r1, r2, r3, r4])
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


def test_sort_by_date_desc(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?sort=desc")
    assert res.status_code == 200
    dates = [r["service_date"] for r in res.json()]
    assert dates == ["2025-11-10", "2025-06-20", "2025-03-05", "2025-01-15"]


def test_sort_by_date_asc(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?sort=asc")
    assert res.status_code == 200
    dates = [r["service_date"] for r in res.json()]
    assert dates == ["2025-01-15", "2025-03-05", "2025-06-20", "2025-11-10"]


def test_sort_by_cost_desc(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?sort=cost_desc")
    assert res.status_code == 200
    costs = [r["cost"] for r in res.json()]
    assert costs == ["5000.00", "3000.00", "1500.00", "0.00"]


def test_sort_by_cost_asc(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?sort=cost_asc")
    assert res.status_code == 200
    costs = [r["cost"] for r in res.json()]
    assert costs == ["0.00", "1500.00", "3000.00", "5000.00"]


def test_sort_with_service_type_filter(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?service_type=Oil%20Change&sort=cost_asc")
    assert res.status_code == 200
    data = res.json()
    assert len(data) == 2
    assert data[0]["cost"] == "0.00"
    assert data[1]["cost"] == "1500.00"


def test_invalid_sort_parameter_rejected(setup_sorting):
    client, v_id = setup_sorting
    res = client.get(f"/vehicles/{v_id}/maintenance?sort=unknown")
    assert res.status_code == 422
