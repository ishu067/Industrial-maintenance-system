from fastapi.testclient import TestClient

from backend.app import app
from backend.db import initialize

initialize()
client = TestClient(app)


def test_health_and_seeded_fleet() -> None:
    assert client.get("/health").json() == {"status": "healthy"}
    response = client.get("/robots")
    assert response.status_code == 200
    assert len(response.json()) >= 3


def test_telemetry_creates_prediction() -> None:
    response = client.post("/telemetry", json={"robot_id": 1, "temperature": 91, "vibration": 6.2, "motor_current": 12, "cycle_count": 98000})
    assert response.status_code == 201
    assert response.json()["risk_level"] == "High"
    predictions = client.get("/predictions").json()
    assert any(item["robot_id"] == 1 for item in predictions)


def test_invalid_robot_is_rejected() -> None:
    response = client.post("/telemetry", json={"robot_id": 9999, "temperature": 40, "vibration": 1, "motor_current": 4, "cycle_count": 100})
    assert response.status_code == 404


def test_reference_level_resources_and_auth() -> None:
    assert len(client.get("/sensors").json()) >= 4
    assert len(client.get("/incidents").json()) >= 1
    assert client.get("/health/robots/1").status_code == 200
    registration = client.post("/auth/register", json={"full_name": "Test Operator", "email": "parity@example.com", "password": "secure123", "confirm_password": "secure123"})
    assert registration.status_code in (201, 400)
    login = client.post("/auth/login", json={"email": "parity@example.com", "password": "secure123"})
    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"
    demo_login = client.post("/auth/login", json={"email": "operator01@robotic-arm.local", "password": "operator123"})
    assert demo_login.status_code == 200


def test_robot_crud_contract() -> None:
    payload = {"name": "ARM-TEST", "model": "QA-1", "manufacturer": "Test Robotics", "serial_number": "QA-001", "location": "Validation Cell", "payload_capacity": 10, "reach": 1.2, "status": "Operational", "installed_on": "2026-09-16"}
    created = client.post("/robots", json=payload)
    assert created.status_code == 201
    robot_id = created.json()["id"]
    assert client.get(f"/robots/{robot_id}").status_code == 200
    assert client.put(f"/robots/{robot_id}", json={**payload, "status": "Inspection"}).json()["status"] == "Inspection"
    assert client.delete(f"/robots/{robot_id}").status_code == 200
