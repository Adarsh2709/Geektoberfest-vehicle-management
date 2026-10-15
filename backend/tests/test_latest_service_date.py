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
def setup_db():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()

    owner = User(username="owner", email="owner@example.com", hashed_password="x")
    db.add(owner)
    db.commit()
    db.refresh(owner)

    v1 = Vehicle(
        make="Hyundai",
        model="i20",
        year=2022,
        registration_number="DL01AA0001",
        current_mileage=15000,
        owner_id=owner.id,
    )
    v2 = Vehicle(
        make="Tata",
        model="Nexon",
        year=2023,
        registration_number="DL01AA0002",
        current_mileage=30000,
        owner_id=owner.id,
    )
    db.add_all([v1, v2])
    db.commit()
    db.refresh(v1)
    db.refresh(v2)

    # v2 has multiple maintenance records created out of chronological order
    r1 = MaintenanceRecord(
        vehicle_id=v2.id,
        service_date=date(2026, 3, 10),
        mileage=10000,
        service_type="Oil Change",
        cost=Decimal("1500.00"),
    )
    r2 = MaintenanceRecord(
        vehicle_id=v2.id,
        service_date=date(2026, 9, 25),
        mileage=25000,
        service_type="General Service",
        cost=Decimal("4500.00"),
    )
    r3 = MaintenanceRecord(
        vehicle_id=v2.id,
        service_date=date(2026, 6, 15),
        mileage=18000,
        service_type="Brake Service",
        cost=Decimal("2200.00"),
    )
    db.add_all([r1, r2, r3])
    db.commit()

    owner_id = owner.id
    v1_id = v1.id
    v2_id = v2.id
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
    yield {"v1_id": v1_id, "v2_id": v2_id}
    app.dependency_overrides.clear()


def test_vehicle_without_maintenance_has_none_last_service_date(setup_db):
    client = TestClient(app)
    v1_id = setup_db["v1_id"]

    res = client.get(f"/vehicles/{v1_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["last_service_date"] is None
    assert data["maintenance_count"] == 0


def test_vehicle_with_out_of_order_records_picks_latest_date(setup_db):
    client = TestClient(app)
    v2_id = setup_db["v2_id"]

    res = client.get(f"/vehicles/{v2_id}")
    assert res.status_code == 200
    data = res.json()
    # The records were dated 2026-03-10, 2026-09-25, 2026-06-15
    assert data["last_service_date"] == "2026-09-25"
    assert data["maintenance_count"] == 3


def test_list_vehicles_includes_correct_latest_service_dates(setup_db):
    client = TestClient(app)
    res = client.get("/vehicles")
    assert res.status_code == 200
    vehicles = {v["registration_number"]: v for v in res.json()}

    assert vehicles["DL01AA0001"]["last_service_date"] is None
    assert vehicles["DL01AA0002"]["last_service_date"] == "2026-09-25"
