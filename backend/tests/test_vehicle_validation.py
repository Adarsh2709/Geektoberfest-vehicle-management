import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.auth import get_current_user
from app.database import Base, get_db
from app.main import app
from app.models import User


@pytest.fixture()
def setup_user():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    db = Session()

    user = User(username="validuser", email="validuser@example.com", hashed_password="x")
    db.add(user)
    db.commit()
    db.refresh(user)
    user_id = user.id
    db.close()

    def override_db():
        session = Session()
        try:
            yield session
        finally:
            session.close()

    class StubUser:
        id = user_id

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = lambda: StubUser()
    yield
    app.dependency_overrides.clear()


def test_create_vehicle_rejects_blank_make(setup_user):
    client = TestClient(app)
    res = client.post("/vehicles", json={
        "make": "   ",
        "model": "Civic",
        "year": 2022,
        "registration_number": "KA01AB1111",
        "current_mileage": 1000
    })
    assert res.status_code == 422
    data = res.json()
    err_msgs = [e["msg"] for e in data["detail"]]
    assert any("cannot be blank" in msg for msg in err_msgs)


def test_create_vehicle_rejects_blank_model(setup_user):
    client = TestClient(app)
    res = client.post("/vehicles", json={
        "make": "Honda",
        "model": "",
        "year": 2022,
        "registration_number": "KA01AB1112",
        "current_mileage": 1000
    })
    assert res.status_code == 422
    data = res.json()
    err_msgs = [e["msg"] for e in data["detail"]]
    assert any("at least 1 character" in msg or "cannot be blank" in msg for msg in err_msgs)


def test_create_vehicle_rejects_invalid_year(setup_user):
    client = TestClient(app)
    res = client.post("/vehicles", json={
        "make": "Honda",
        "model": "Civic",
        "year": 1800,
        "registration_number": "KA01AB1113",
        "current_mileage": 1000
    })
    assert res.status_code == 422
    data = res.json()
    assert any("greater than or equal to 1886" in e["msg"] for e in data["detail"])


def test_create_vehicle_rejects_negative_mileage(setup_user):
    client = TestClient(app)
    res = client.post("/vehicles", json={
        "make": "Honda",
        "model": "Civic",
        "year": 2022,
        "registration_number": "KA01AB1114",
        "current_mileage": -50
    })
    assert res.status_code == 422
    data = res.json()
    assert any("greater than or equal to 0" in e["msg"] for e in data["detail"])


def test_create_vehicle_rejects_blank_registration(setup_user):
    client = TestClient(app)
    res = client.post("/vehicles", json={
        "make": "Honda",
        "model": "Civic",
        "year": 2022,
        "registration_number": "   ",
        "current_mileage": 1000
    })
    assert res.status_code == 422
    data = res.json()
    assert any("cannot be blank" in e["msg"] for e in data["detail"])
