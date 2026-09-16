from dataclasses import dataclass


@dataclass(frozen=True)
class RiskAssessment:
    score: float
    level: str
    recommendation: str


def assess(temperature: float, vibration: float, motor_current: float, cycle_count: int) -> RiskAssessment:
    """A deterministic baseline model that is explainable and easy to replace."""
    thermal = max(0.0, (temperature - 55.0) / 35.0)
    vibration_load = max(0.0, (vibration - 2.5) / 4.0)
    current_load = max(0.0, (motor_current - 7.0) / 8.0)
    cycle_load = max(0.0, (cycle_count - 70000) / 120000)
    score = round(min(1.0, 0.35 * thermal + 0.30 * vibration_load + 0.20 * current_load + 0.15 * cycle_load), 3)
    if score >= 0.65:
        level, recommendation = "High", "Schedule an inspection before the next production shift."
    elif score >= 0.35:
        level, recommendation = "Medium", "Monitor the next 500 cycles and plan preventive maintenance."
    else:
        level, recommendation = "Low", "Continue normal operation and routine monitoring."
    return RiskAssessment(score, level, recommendation)
