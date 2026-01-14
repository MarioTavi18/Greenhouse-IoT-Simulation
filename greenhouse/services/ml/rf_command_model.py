from __future__ import annotations

from pathlib import Path
import joblib
import pandas as pd

EQUIPMENT = [
    "heater", "ventilation", "irrigation",
    "co2_injector", "lights", "dehumidifier", "light_blinds"
]

FEATURES = [
    "temperature", "humidity", "soil_moisture", "light_intensity", "co2_concentration",
    "prev_heater", "prev_ventilation", "prev_irrigation",
    "prev_co2_injector", "prev_lights", "prev_dehumidifier", "prev_light_blinds",
]


class RFCommandModel:
    def __init__(self, model_dir: str | Path = "trained_models"):
        model_dir = Path(model_dir)
        self.models = {name: joblib.load(model_dir / f"rf_{name}.joblib") for name in EQUIPMENT}

    def decide(self, features: dict) -> dict:
        # Build a DataFrame with correct column names and order
        row = {k: features[k] for k in FEATURES}
        X = pd.DataFrame([row], columns=FEATURES)

        out = {}
        for name, clf in self.models.items():
            out[name] = bool(clf.predict(X)[0])
        return out