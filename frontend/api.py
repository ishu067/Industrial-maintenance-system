import os
from typing import Any

import requests

BASE_URL = os.getenv("ROBOTIC_ARM_API_URL", "http://127.0.0.1:8000")


def get(path: str) -> Any:
    response = requests.get(f"{BASE_URL}{path}", timeout=5)
    response.raise_for_status()
    return response.json()


def post(path: str, payload: dict[str, Any]) -> Any:
    response = requests.post(f"{BASE_URL}{path}", json=payload, timeout=5)
    response.raise_for_status()
    return response.json()


def health() -> dict[str, str]:
    return get("/health")


def robots() -> list[dict[str, Any]]:
    return get("/robots")


def latest_telemetry() -> list[dict[str, Any]]:
    return get("/telemetry/latest")


def predictions() -> list[dict[str, Any]]:
    return get("/predictions")


def maintenance() -> list[dict[str, Any]]:
    return get("/maintenance")


def sensors() -> list[dict[str, Any]]:
    return get("/sensors")


def incidents() -> list[dict[str, Any]]:
    return get("/incidents")


def notifications() -> list[dict[str, Any]]:
    return get("/notifications")


def robot_health(robot_id: int) -> dict[str, Any]:
    return get(f"/health/robots/{robot_id}")


def login(email: str, password: str) -> dict[str, Any]:
    return post("/auth/login", {"email": email, "password": password})


def register(full_name: str, email: str, password: str, confirm_password: str) -> dict[str, Any]:
    return post("/auth/register", {"full_name": full_name, "email": email, "password": password, "confirm_password": confirm_password})


def submit_telemetry(payload: dict[str, Any]) -> dict[str, Any]:
    return post("/telemetry", payload)


def create_maintenance(payload: dict[str, Any]) -> dict[str, Any]:
    return post("/maintenance", payload)
