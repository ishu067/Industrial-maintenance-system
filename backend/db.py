from __future__ import annotations

import os
import sqlite3
import hashlib
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = Path(os.getenv("ROBOTIC_ARM_DB", ROOT / "robotic_arm.db"))


def connect() -> sqlite3.Connection:
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def initialize() -> None:
    with connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS robots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                model TEXT NOT NULL,
                manufacturer TEXT NOT NULL DEFAULT 'Industrial Robotics',
                serial_number TEXT NOT NULL DEFAULT '',
                location TEXT NOT NULL,
                payload_capacity REAL NOT NULL DEFAULT 0,
                reach REAL NOT NULL DEFAULT 0,
                status TEXT NOT NULL DEFAULT 'Operational',
                installed_on TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'operator'
            );
            CREATE TABLE IF NOT EXISTS sensors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL REFERENCES robots(id),
                sensor_type TEXT NOT NULL,
                name TEXT NOT NULL,
                unit TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Online',
                last_value REAL
            );
            CREATE TABLE IF NOT EXISTS telemetry (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL REFERENCES robots(id),
                temperature REAL NOT NULL,
                vibration REAL NOT NULL,
                motor_current REAL NOT NULL,
                cycle_count INTEGER NOT NULL,
                axis_1 REAL NOT NULL DEFAULT 0,
                axis_2 REAL NOT NULL DEFAULT 0,
                axis_3 REAL NOT NULL DEFAULT 0,
                axis_4 REAL NOT NULL DEFAULT 0,
                axis_5 REAL NOT NULL DEFAULT 0,
                axis_6 REAL NOT NULL DEFAULT 0,
                recorded_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS predictions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL REFERENCES robots(id),
                risk_score REAL NOT NULL,
                risk_level TEXT NOT NULL,
                recommendation TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS maintenance (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL REFERENCES robots(id),
                title TEXT NOT NULL,
                priority TEXT NOT NULL,
                due_date TEXT NOT NULL,
                completed INTEGER NOT NULL DEFAULT 0
            );
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER NOT NULL REFERENCES robots(id),
                title TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                description TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE TABLE IF NOT EXISTS notifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                robot_id INTEGER REFERENCES robots(id),
                title TEXT NOT NULL,
                message TEXT NOT NULL,
                severity TEXT NOT NULL DEFAULT 'Info',
                read INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            """
        )
        for statement in (
            "ALTER TABLE robots ADD COLUMN manufacturer TEXT NOT NULL DEFAULT 'Industrial Robotics'",
            "ALTER TABLE robots ADD COLUMN serial_number TEXT NOT NULL DEFAULT ''",
            "ALTER TABLE robots ADD COLUMN payload_capacity REAL NOT NULL DEFAULT 0",
            "ALTER TABLE robots ADD COLUMN reach REAL NOT NULL DEFAULT 0",
        ):
            try:
                connection.execute(statement)
            except sqlite3.OperationalError:
                pass
        for axis in range(1, 7):
            try:
                connection.execute(f"ALTER TABLE telemetry ADD COLUMN axis_{axis} REAL NOT NULL DEFAULT 0")
            except sqlite3.OperationalError:
                pass
        _align_reference_columns(connection)
        if connection.execute("SELECT COUNT(*) FROM robots").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO robots(name, model, manufacturer, serial_number, location, payload_capacity, reach, status, installed_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                [
                    ("ARM-1001", "RX-220", "KUKA", "KR220-001", "Assembly Line A", 220, 2.7, "Operational", "2024-02-18"),
                    ("ARM-1002", "RX-220", "KUKA", "KR220-002", "Assembly Line B", 220, 2.7, "Operational", "2024-04-09"),
                    ("ARM-1003", "TX-410", "Fanuc", "TX410-003", "Welding Cell 1", 165, 2.1, "Inspection", "2023-11-27"),
                ],
            )
            connection.executemany(
                "INSERT INTO maintenance(robot_id, title, priority, due_date) VALUES (?, ?, ?, ?)",
                [(1, "Lubricate wrist joints", "Medium", "2026-09-20"), (3, "Inspect motor coupling", "High", "2026-09-17")],
            )
            connection.executemany(
                "INSERT INTO sensors(robot_id, sensor_type, name, unit, last_value) VALUES (?, ?, ?, ?, ?)",
                [(1, "Temperature", "Wrist temperature", "°C", 48.2), (1, "Vibration", "Base vibration", "mm/s", 1.8), (2, "Current", "Motor current", "A", 5.2), (3, "Temperature", "Joint temperature", "°C", 61.4)],
            )
            connection.execute("INSERT INTO incidents(robot_id, title, severity, description) VALUES (3, 'Elevated joint temperature', 'High', 'Temperature exceeded the inspection threshold during the last shift.')")
            connection.execute("INSERT INTO notifications(robot_id, title, message, severity) VALUES (3, 'Inspection required', 'ARM-1003 has an open high-severity incident.', 'High')")
        if connection.execute("SELECT COUNT(*) FROM sensors").fetchone()[0] == 0:
            connection.executemany(
                "INSERT INTO sensors(robot_id, sensor_type, name, unit, last_value) VALUES (?, ?, ?, ?, ?)",
                [(1, "Temperature", "Wrist temperature", "°C", 48.2), (1, "Vibration", "Base vibration", "mm/s", 1.8), (2, "Current", "Motor current", "A", 5.2), (3, "Temperature", "Joint temperature", "°C", 61.4)],
            )
        if connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0] == 0:
            connection.execute("INSERT INTO incidents(robot_id, title, severity, description) VALUES (3, 'Elevated joint temperature', 'High', 'Temperature exceeded the inspection threshold during the last shift.')")
        if connection.execute("SELECT COUNT(*) FROM notifications").fetchone()[0] == 0:
            connection.execute("INSERT INTO notifications(robot_id, title, message, severity) VALUES (3, 'Inspection required', 'ARM-1003 has an open high-severity incident.', 'High')")
        _ensure_demo_rows(connection, target=50)
        connection.execute("""UPDATE telemetry SET
            axis_1 = CASE WHEN axis_1 = 0 THEN motor_current * 0.92 ELSE axis_1 END,
            axis_2 = CASE WHEN axis_2 = 0 THEN motor_current * 0.81 ELSE axis_2 END,
            axis_3 = CASE WHEN axis_3 = 0 THEN motor_current * 0.74 ELSE axis_3 END,
            axis_4 = CASE WHEN axis_4 = 0 THEN motor_current * 0.68 ELSE axis_4 END,
            axis_5 = CASE WHEN axis_5 = 0 THEN motor_current * 0.59 ELSE axis_5 END,
            axis_6 = CASE WHEN axis_6 = 0 THEN motor_current * 0.47 ELSE axis_6 END
        """)
        _align_reference_columns(connection)


def _ensure_demo_rows(connection: sqlite3.Connection, target: int) -> None:
    """Fill every demo table to a stable row count without duplicating records."""
    robot_count = connection.execute("SELECT COUNT(*) FROM robots").fetchone()[0]
    for index in range(robot_count + 1, target + 1):
        connection.execute(
            "INSERT INTO robots(name, model, manufacturer, serial_number, location, payload_capacity, reach, status, installed_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (f"ARM-{1000 + index}", f"RX-{200 + index % 30}", "KUKA" if index % 2 else "Fanuc", f"DEMO-{index:04d}", f"Assembly Line {(index % 10) + 1}", 100 + index % 150, round(1.5 + (index % 15) / 10, 1), "Operational" if index % 5 else "Inspection", "2025-01-15"),
        )

    robot_ids = [item[0] for item in connection.execute("SELECT id FROM robots ORDER BY id").fetchall()]
    row_count = connection.execute("SELECT COUNT(*) FROM sensors").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        robot_id = robot_ids[(index - 1) % len(robot_ids)]
        connection.execute(
            "INSERT INTO sensors(robot_id, sensor_type, name, unit, last_value) VALUES (?, ?, ?, ?, ?)",
            (robot_id, ("Temperature", "Vibration", "Current")[index % 3], f"Sensor-{index:03d}", "°C" if index % 3 == 1 else "mm/s" if index % 3 == 2 else "A", round(2.0 + index * 0.7, 2)),
        )

    row_count = connection.execute("SELECT COUNT(*) FROM telemetry").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        robot_id = robot_ids[(index - 1) % len(robot_ids)]
        connection.execute(
            "INSERT INTO telemetry(robot_id, temperature, vibration, motor_current, cycle_count, axis_1, axis_2, axis_3, axis_4, axis_5, axis_6) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (robot_id, 42 + index % 30, round(1.0 + (index % 20) / 10, 2), round(4.0 + index % 8, 2), 20_000 + index * 1_000, 4.2 + index % 6, 3.8 + index % 6, 3.1 + index % 6, 2.9 + index % 6, 2.4 + index % 6, 1.8 + index % 6),
        )

    row_count = connection.execute("SELECT COUNT(*) FROM predictions").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        robot_id = robot_ids[(index - 1) % len(robot_ids)]
        score = round(min(0.95, 0.1 + (index % 10) / 20), 3)
        level = "High" if score >= 0.65 else "Medium" if score >= 0.35 else "Low"
        connection.execute(
            "INSERT INTO predictions(robot_id, risk_score, risk_level, recommendation) VALUES (?, ?, ?, ?)",
            (robot_id, score, level, "Schedule inspection." if level == "High" else "Continue routine monitoring."),
        )

    row_count = connection.execute("SELECT COUNT(*) FROM maintenance").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        connection.execute(
            "INSERT INTO maintenance(robot_id, title, priority, due_date) VALUES (?, ?, ?, ?)",
            (robot_ids[(index - 1) % len(robot_ids)], f"Preventive service {index:03d}", ("Low", "Medium", "High")[index % 3], "2026-10-15"),
        )

    row_count = connection.execute("SELECT COUNT(*) FROM incidents").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        connection.execute(
            "INSERT INTO incidents(robot_id, title, severity, description) VALUES (?, ?, ?, ?)",
            (robot_ids[(index - 1) % len(robot_ids)], f"Operational review {index:03d}", "High" if index % 4 == 0 else "Medium", "Generated demo incident for operational review."),
        )

    row_count = connection.execute("SELECT COUNT(*) FROM notifications").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        connection.execute(
            "INSERT INTO notifications(robot_id, title, message, severity) VALUES (?, ?, ?, ?)",
            (robot_ids[(index - 1) % len(robot_ids)], f"Fleet update {index:03d}", "Review the latest robot operating data.", "Info" if index % 4 else "High"),
        )

    salt = "demo-salt"
    digest = hashlib.pbkdf2_hmac("sha256", b"operator123", salt.encode(), 120_000).hex()
    if not connection.execute("SELECT id FROM users WHERE email = ?", ("operator01@robotic-arm.local",)).fetchone():
        if connection.execute("SELECT COUNT(*) FROM users").fetchone()[0] >= target:
            connection.execute("DELETE FROM users WHERE id = (SELECT MAX(id) FROM users)")
        connection.execute(
            "INSERT OR IGNORE INTO users(full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            ("Demo Operator 01", "operator01@robotic-arm.local", f"{salt}${digest}", "operator"),
        )
    row_count = connection.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    for index in range(row_count + 1, target + 1):
        connection.execute(
            "INSERT OR IGNORE INTO users(full_name, email, password_hash, role) VALUES (?, ?, ?, ?)",
            (f"Demo Operator {index:02d}", f"operator{index:02d}@robotic-arm.local", f"{salt}${digest}", "operator"),
        )


def _align_reference_columns(connection: sqlite3.Connection) -> None:
    """Add the reference project's domain names and populate them from local fields."""
    reference_columns = {
        "robots": {"robot_id": "INTEGER", "robot_name": "TEXT", "installation_date": "TEXT"},
        "users": {"user_id": "INTEGER", "phone": "TEXT", "created_at": "TEXT"},
        "sensors": {"sensor_id": "INTEGER", "sensor_name": "TEXT", "manufacturer": "TEXT"},
        "telemetry": {
            "telemetry_id": "INTEGER", "Current_J0": "REAL", "Temperature_T0": "REAL",
            "Current_J1": "REAL", "Temperature_J1": "REAL", "Current_J2": "REAL", "Temperature_J2": "REAL",
            "Current_J3": "REAL", "Temperature_J3": "REAL", "Current_J4": "REAL", "Temperature_J4": "REAL",
            "Current_J5": "REAL", "Temperature_J5": "REAL", "Speed_J0": "REAL", "Speed_J1": "REAL",
            "Speed_J2": "REAL", "Speed_J3": "REAL", "Speed_J4": "REAL", "Speed_J5": "REAL",
            "Tool_current": "REAL", "cycle": "REAL", "timestamp": "TEXT",
        },
        "predictions": {"prediction_id": "INTEGER", "failure_probability": "REAL", "predicted_fault": "TEXT", "confidence": "REAL", "prediction_time": "TEXT"},
        "maintenance": {"maintenance_id": "INTEGER", "maintenance_type": "TEXT", "technician_name": "TEXT", "maintenance_date": "TEXT", "next_due_date": "TEXT", "remarks": "TEXT"},
        "incidents": {"incident_id": "INTEGER", "incident_type": "TEXT", "resolved": "INTEGER", "incident_time": "TEXT"},
        "notifications": {"notification_id": "INTEGER", "alert_type": "TEXT", "priority": "TEXT", "status": "TEXT"},
    }
    for table, columns in reference_columns.items():
        existing = {item[1] for item in connection.execute(f"PRAGMA table_info({table})").fetchall()}
        for column, column_type in columns.items():
            if column not in existing:
                connection.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")

    connection.execute("UPDATE robots SET robot_id = id, robot_name = name, installation_date = installed_on WHERE robot_id IS NULL OR robot_name IS NULL")
    connection.execute("UPDATE users SET user_id = id, phone = COALESCE(phone, ''), created_at = COALESCE(created_at, CURRENT_TIMESTAMP) WHERE user_id IS NULL")
    connection.execute("UPDATE sensors SET sensor_id = id, sensor_name = name, manufacturer = COALESCE(manufacturer, 'Industrial Robotics') WHERE sensor_id IS NULL OR sensor_name IS NULL")
    connection.execute("""UPDATE telemetry SET
        telemetry_id = id, Current_J0 = COALESCE(Current_J0, axis_1), Temperature_T0 = COALESCE(Temperature_T0, temperature),
        Current_J1 = COALESCE(Current_J1, axis_2), Temperature_J1 = COALESCE(Temperature_J1, temperature),
        Current_J2 = COALESCE(Current_J2, axis_3), Temperature_J2 = COALESCE(Temperature_J2, temperature),
        Current_J3 = COALESCE(Current_J3, axis_4), Temperature_J3 = COALESCE(Temperature_J3, temperature),
        Current_J4 = COALESCE(Current_J4, axis_5), Temperature_J4 = COALESCE(Temperature_J4, temperature),
        Current_J5 = COALESCE(Current_J5, axis_6), Temperature_J5 = COALESCE(Temperature_J5, temperature),
        Speed_J0 = COALESCE(Speed_J0, axis_1), Speed_J1 = COALESCE(Speed_J1, axis_2), Speed_J2 = COALESCE(Speed_J2, axis_3),
        Speed_J3 = COALESCE(Speed_J3, axis_4), Speed_J4 = COALESCE(Speed_J4, axis_5), Speed_J5 = COALESCE(Speed_J5, axis_6),
        Tool_current = COALESCE(Tool_current, motor_current), cycle = COALESCE(cycle, cycle_count), timestamp = COALESCE(timestamp, recorded_at)
    WHERE telemetry_id IS NULL""")
    connection.execute("UPDATE predictions SET prediction_id = id, failure_probability = COALESCE(failure_probability, risk_score), predicted_fault = COALESCE(predicted_fault, risk_level), confidence = COALESCE(confidence, 1 - risk_score), prediction_time = COALESCE(prediction_time, created_at) WHERE prediction_id IS NULL")
    connection.execute("UPDATE maintenance SET maintenance_id = id, maintenance_type = COALESCE(maintenance_type, title), technician_name = COALESCE(technician_name, 'Operations Team'), maintenance_date = COALESCE(maintenance_date, due_date), next_due_date = COALESCE(next_due_date, due_date), remarks = COALESCE(remarks, '') WHERE maintenance_id IS NULL")
    connection.execute("UPDATE incidents SET incident_id = id, incident_type = COALESCE(incident_type, title), resolved = CASE WHEN resolved IS NULL THEN CASE WHEN status = 'Resolved' THEN 1 ELSE 0 END ELSE resolved END, incident_time = COALESCE(incident_time, created_at) WHERE incident_id IS NULL")
    connection.execute("UPDATE notifications SET notification_id = id, alert_type = COALESCE(alert_type, title), priority = COALESCE(priority, severity), status = COALESCE(status, CASE WHEN read = 1 THEN 'Read' ELSE 'Unread' END) WHERE notification_id IS NULL")


def rows(query: str, parameters: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
    with connect() as connection:
        return [dict(row) for row in connection.execute(query, parameters).fetchall()]


def row(query: str, parameters: tuple[Any, ...] = ()) -> dict[str, Any] | None:
    result = rows(query, parameters)
    return result[0] if result else None
