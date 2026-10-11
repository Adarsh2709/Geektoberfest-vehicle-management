"""Tests for maintenance receipt upload/download access control.

Run from backend/: pytest -q
"""

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import MaintenanceRecord, User, Vehicle
from app.routes import maintenance as maintenance_routes

PDF_BYTES = b"%PDF-1.4 fake receipt for tests"
JPG_BYTES = b"\xff\xd8\xff fake jpg bytes"


@pytest.fixture()
def setup(tmp_path):
    maintenance_routes.settings.receipt_dir = str(tmp_path)
    maintenance_routes.settings.max_receipt_mb = 5

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
        registration_number="KA01RX0001", current_mileage=1000, owner_id=owner.id,
    )
    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    record = MaintenanceRecord(
        vehicle_id=vehicle.id, service_date=date(2026, 1, 10),
        mileage=1000, service_type="Oil Change", cost=Decimal("120.00"),
    )
    db.add(record)
    db.commit()
    db.refresh(record)
    ids = {"owner": owner.id, "stranger": stranger.id, "record": record.id}
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    def as_user(user_id):
        class StubUser:
            id = user_id
        return StubUser()

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: as_user(ids["owner"])
    yield {"ids": ids, "dir": tmp_path, "as_user": as_user}
    app.dependency_overrides.clear()


def _upload(client, record_id, name="bill.pdf", content=PDF_BYTES, content_type="application/pdf"):
    return client.post(
        f"/maintenance/{record_id}/receipt",
        files={"file": (name, content, content_type)},
    )


def test_valid_upload_stores_file_and_metadata(setup):
    client = TestClient(app)
    response = _upload(client, setup["ids"]["record"])
    assert response.status_code == 201
    body = response.json()
    assert body["receipt_original_name"] == "bill.pdf"
    assert body["receipt_size"] == len(PDF_BYTES)
    stored = list(setup["dir"].iterdir())
    assert len(stored) == 1
    assert stored[0].read_bytes() == PDF_BYTES
    assert ".." not in stored[0].name


def test_invalid_type_is_rejected_without_record_change(setup):
    client = TestClient(app)
    before = client.get(f"/maintenance/{setup['ids']['record']}").json()
    response = _upload(
        client, setup["ids"]["record"],
        name="evil.exe", content=b"MZ", content_type="application/x-msdownload",
    )
    assert response.status_code == 422
    after = client.get(f"/maintenance/{setup['ids']['record']}").json()
    assert after["receipt_original_name"] is None
    assert before["receipt_original_name"] is None
    assert list(setup["dir"].iterdir()) == []


def test_oversize_upload_is_rejected(setup):
    client = TestClient(app)
    big = b"x" * (6 * 1024 * 1024)
    response = _upload(client, setup["ids"]["record"], content=big)
    assert response.status_code == 413
    assert list(setup["dir"].iterdir()) == []
    body = client.get(f"/maintenance/{setup['ids']['record']}").json()
    assert body["receipt_original_name"] is None


def test_owner_can_download_and_stranger_cannot(setup):
    client = TestClient(app)
    assert _upload(client, setup["ids"]["record"]).status_code == 201
    response = client.get(f"/maintenance/{setup['ids']['record']}/receipt")
    assert response.status_code == 200
    assert response.content == PDF_BYTES

    app.dependency_overrides[get_current_user] = lambda: setup["as_user"](setup["ids"]["stranger"])
    try:
        assert client.get(f"/maintenance/{setup['ids']['record']}/receipt").status_code == 404
        assert _upload(client, setup["ids"]["record"]).status_code == 404
    finally:
        app.dependency_overrides[get_current_user] = lambda: setup["as_user"](setup["ids"]["owner"])


def test_delete_receipt_and_missing_receipt(setup):
    client = TestClient(app)
    record_id = setup["ids"]["record"]
    assert client.get(f"/maintenance/{record_id}/receipt").status_code == 404
    assert _upload(client, record_id).status_code == 201
    assert len(list(setup["dir"].iterdir())) == 1
    assert client.delete(f"/maintenance/{record_id}/receipt").status_code == 204
    assert list(setup["dir"].iterdir()) == []
    assert client.get(f"/maintenance/{record_id}/receipt").status_code == 404
