import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import User, Vehicle


@pytest.fixture()
def setup():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()
    owner = User(username="owner", email="owner@example.com", hashed_password="x")
    stranger = User(username="stranger", email="stranger@example.com", hashed_password="x")
    db.add_all([owner, stranger])
    db.commit()
    db.refresh(owner)
    db.refresh(stranger)
    db.add_all([
        Vehicle(make="Maruti", model="Swift", year=2020, registration_number="KA01AB1234", current_mileage=50000, owner_id=owner.id),
        Vehicle(make="Honda", model="City", year=2021, registration_number="MH02CD5678", current_mileage=10000, owner_id=stranger.id),
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


def test_registration_search_is_case_insensitive_partial_and_trims_outer_whitespace(setup):
    response = TestClient(app).get("/vehicles", params={"registration_number": "  ab123  "})

    assert response.status_code == 200
    assert [vehicle["registration_number"] for vehicle in response.json()] == ["KA01AB1234"]


def test_registration_search_only_returns_signed_in_users_vehicles(setup):
    response = TestClient(app).get("/vehicles", params={"registration_number": "CD5678"})

    assert response.status_code == 200
    assert response.json() == []


def test_registration_search_preserves_internal_whitespace(setup):
    response = TestClient(app).get("/vehicles", params={"registration_number": "AB 123"})

    assert response.status_code == 200
    assert response.json() == []
