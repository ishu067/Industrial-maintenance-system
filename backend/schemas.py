from datetime import date
from pydantic import BaseModel, Field


class TelemetryInput(BaseModel):
    robot_id: int
    temperature: float = Field(ge=0, le=150)
    vibration: float = Field(ge=0, le=20)
    motor_current: float = Field(ge=0, le=50)
    cycle_count: int = Field(ge=0)
    axis_1: float = Field(default=0, ge=-100, le=100)
    axis_2: float = Field(default=0, ge=-100, le=100)
    axis_3: float = Field(default=0, ge=-100, le=100)
    axis_4: float = Field(default=0, ge=-100, le=100)
    axis_5: float = Field(default=0, ge=-100, le=100)
    axis_6: float = Field(default=0, ge=-100, le=100)


class MaintenanceInput(BaseModel):
    robot_id: int
    title: str = Field(min_length=3, max_length=120)
    priority: str = Field(pattern="^(Low|Medium|High)$")
    due_date: date


class RobotInput(BaseModel):
    name: str = Field(min_length=2, max_length=100)
    model: str = Field(min_length=1, max_length=100)
    manufacturer: str = Field(min_length=1, max_length=100)
    serial_number: str = Field(min_length=1, max_length=100)
    location: str = Field(min_length=1, max_length=150)
    payload_capacity: float = Field(ge=0)
    reach: float = Field(ge=0)
    status: str = Field(pattern="^(Operational|Inspection|Maintenance|Inactive)$")
    installed_on: date


class AuthInput(BaseModel):
    email: str
    password: str = Field(min_length=6)


class RegisterInput(AuthInput):
    full_name: str = Field(min_length=2, max_length=100)
    confirm_password: str = Field(min_length=6)
