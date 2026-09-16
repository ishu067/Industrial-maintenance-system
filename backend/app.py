from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from backend.db import connect, initialize, row, rows
from backend.ml.risk import assess
from backend.auth import login, register
from backend.schemas import AuthInput, MaintenanceInput, RegisterInput, RobotInput, TelemetryInput

app = FastAPI(title="Robotic Arm Operations API", version="1.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    initialize()


@app.get("/")
def root() -> dict[str, str]:
    return {"service": "robotic-arm-operations", "status": "ready"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "healthy"}


@app.get("/robots")
def get_robots() -> list[dict]:
    return rows("SELECT * FROM robots ORDER BY name")


@app.get("/robots/{robot_id}")
def get_robot(robot_id: int) -> dict:
    robot = row("SELECT * FROM robots WHERE id = ?", (robot_id,))
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    return robot


@app.post("/robots", status_code=201)
def create_robot(payload: RobotInput) -> dict:
    values = payload.model_dump()
    values["installed_on"] = values["installed_on"].isoformat()
    with connect() as connection:
        try:
            cursor = connection.execute(
                "INSERT INTO robots(name, model, manufacturer, serial_number, location, payload_capacity, reach, status, installed_on) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
                tuple(values.values()),
            )
        except Exception as error:
            raise HTTPException(status_code=400, detail="Robot name or serial number already exists") from error
    return row("SELECT * FROM robots WHERE id = ?", (cursor.lastrowid,))


@app.put("/robots/{robot_id}")
def update_robot(robot_id: int, payload: RobotInput) -> dict:
    if not row("SELECT id FROM robots WHERE id = ?", (robot_id,)):
        raise HTTPException(status_code=404, detail="Robot not found")
    values = payload.model_dump()
    values["installed_on"] = values["installed_on"].isoformat()
    with connect() as connection:
        connection.execute(
            "UPDATE robots SET name=?, model=?, manufacturer=?, serial_number=?, location=?, payload_capacity=?, reach=?, status=?, installed_on=? WHERE id=?",
            (*values.values(), robot_id),
        )
    return row("SELECT * FROM robots WHERE id = ?", (robot_id,))


@app.delete("/robots/{robot_id}")
def delete_robot(robot_id: int) -> dict[str, str]:
    if not row("SELECT id FROM robots WHERE id = ?", (robot_id,)):
        raise HTTPException(status_code=404, detail="Robot not found")
    with connect() as connection:
        connection.execute("DELETE FROM robots WHERE id = ?", (robot_id,))
    return {"message": "Robot deleted successfully"}


@app.post("/auth/register", status_code=201)
def register_user(payload: RegisterInput) -> dict:
    if payload.password != payload.confirm_password:
        raise HTTPException(status_code=400, detail="Passwords do not match")
    try:
        return register(payload.full_name, payload.email, payload.password)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.post("/auth/login")
def login_user(payload: AuthInput) -> dict:
    result = login(payload.email, payload.password)
    if not result:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return result


@app.get("/sensors")
def get_sensors() -> list[dict]:
    return rows("SELECT s.*, r.name AS robot_name FROM sensors s JOIN robots r ON r.id = s.robot_id ORDER BY r.name, s.name")


@app.get("/incidents")
def get_incidents() -> list[dict]:
    return rows("SELECT i.*, r.name AS robot_name FROM incidents i JOIN robots r ON r.id = i.robot_id ORDER BY i.status, i.created_at DESC")


@app.get("/notifications")
def get_notifications() -> list[dict]:
    return rows("SELECT n.*, r.name AS robot_name FROM notifications n LEFT JOIN robots r ON r.id = n.robot_id ORDER BY n.read, n.created_at DESC")


@app.get("/health/robots/{robot_id}")
def robot_health(robot_id: int) -> dict:
    robot = row("SELECT id, name, status FROM robots WHERE id = ?", (robot_id,))
    telemetry = row("SELECT * FROM telemetry WHERE robot_id = ? ORDER BY id DESC LIMIT 1", (robot_id,))
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    if not telemetry:
        return {**robot, "health_score": None, "health_status": "No data"}
    assessment = assess(telemetry["temperature"], telemetry["vibration"], telemetry["motor_current"], telemetry["cycle_count"])
    return {**robot, "health_score": round((1 - assessment.score) * 100, 1), "health_status": "Critical" if assessment.level == "High" else "Warning" if assessment.level == "Medium" else "Good"}


@app.get("/telemetry/latest")
def latest_telemetry() -> list[dict]:
    return rows(
        """SELECT r.name, r.location, t.temperature, t.vibration, t.motor_current, t.cycle_count,
                  t.axis_1, t.axis_2, t.axis_3, t.axis_4, t.axis_5, t.axis_6, t.recorded_at
           FROM robots r JOIN telemetry t ON t.robot_id = r.id
           WHERE t.id IN (SELECT MAX(id) FROM telemetry GROUP BY robot_id) ORDER BY r.name"""
    )


@app.get("/predictions")
def get_predictions() -> list[dict]:
    return rows(
        """SELECT p.*, r.name AS robot_name, r.location FROM predictions p
           JOIN robots r ON r.id = p.robot_id
           WHERE p.id IN (SELECT MAX(id) FROM predictions GROUP BY robot_id)
           ORDER BY p.risk_score DESC"""
    )


@app.get("/maintenance")
def get_maintenance() -> list[dict]:
    return rows("SELECT m.*, r.name AS robot_name FROM maintenance m JOIN robots r ON r.id = m.robot_id ORDER BY m.completed, m.due_date")


@app.post("/telemetry", status_code=201)
def record_telemetry(payload: TelemetryInput) -> dict:
    robot = row("SELECT id FROM robots WHERE id = ?", (payload.robot_id,))
    if not robot:
        raise HTTPException(status_code=404, detail="Robot not found")
    assessment = assess(payload.temperature, payload.vibration, payload.motor_current, payload.cycle_count)
    with connect() as connection:
        connection.execute(
            "INSERT INTO telemetry(robot_id, temperature, vibration, motor_current, cycle_count, axis_1, axis_2, axis_3, axis_4, axis_5, axis_6) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (payload.robot_id, payload.temperature, payload.vibration, payload.motor_current, payload.cycle_count, payload.axis_1, payload.axis_2, payload.axis_3, payload.axis_4, payload.axis_5, payload.axis_6),
        )
        cursor = connection.execute(
            "INSERT INTO predictions(robot_id, risk_score, risk_level, recommendation) VALUES (?, ?, ?, ?)",
            (payload.robot_id, assessment.score, assessment.level, assessment.recommendation),
        )
    return {"prediction_id": cursor.lastrowid, "risk_score": assessment.score, "risk_level": assessment.level, "recommendation": assessment.recommendation}


@app.post("/maintenance", status_code=201)
def add_maintenance(payload: MaintenanceInput) -> dict:
    if not row("SELECT id FROM robots WHERE id = ?", (payload.robot_id,)):
        raise HTTPException(status_code=404, detail="Robot not found")
    with connect() as connection:
        cursor = connection.execute(
            "INSERT INTO maintenance(robot_id, title, priority, due_date) VALUES (?, ?, ?, ?)",
            (payload.robot_id, payload.title, payload.priority, payload.due_date.isoformat()),
        )
    return {"id": cursor.lastrowid, "status": "created"}
