from backend.ml.risk import assess


def predict_protective_stop(data: dict) -> dict:
    """Adapt the operational feature dictionary to the shared risk model."""
    assessment = assess(
        float(data.get("temperature", data.get("Temperature_T0", 0))),
        float(data.get("vibration", 0)),
        float(data.get("motor_current", data.get("Tool_current", 0))),
        int(data.get("cycle_count", data.get("cycle", 0))),
    )
    return {
        "prediction": int(assessment.level == "High"),
        "protective_stop": assessment.level == "High",
        "probability": assessment.score,
        "threshold": 0.65,
        "risk_level": assessment.level,
        "recommendation": assessment.recommendation,
    }


if __name__ == "__main__":
    print(predict_protective_stop({"temperature": 82, "vibration": 5.1, "motor_current": 10, "cycle_count": 90000}))