"""Write the baseline model configuration used by the explainable scorer."""

import json
from pathlib import Path


CONFIG_PATH = Path(__file__).with_name("model_config.json")


def train() -> dict:
    configuration = {"model": "weighted-threshold-baseline", "threshold": 0.65, "features": ["temperature", "vibration", "motor_current", "cycle_count"]}
    CONFIG_PATH.write_text(json.dumps(configuration, indent=2), encoding="utf-8")
    return configuration


if __name__ == "__main__":
    print(train())