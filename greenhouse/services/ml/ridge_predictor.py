from __future__ import annotations

from pathlib import Path
import numpy as np
import joblib

METRICS = ["temperature", "humidity", "soil_moisture", "light_intensity", "co2_concentration"]


class RidgeNextTickPredictor:
    """
    Loads ridge_next_tick.joblib bundle:
      bundle["model"], bundle["x_scaler"], bundle["y_scaler"]
    Predicts next tick metrics from last 10 readings (shape: (10,5)).
    """

    def __init__(self, model_path: str | Path = "trained_models/ridge_next_tick.joblib"):
        bundle = joblib.load(str(model_path))
        self.model = bundle["model"]
        self.x_scaler = bundle["x_scaler"]
        self.y_scaler = bundle["y_scaler"]

    def predict_next(self, last_10: np.ndarray) -> dict:
        """
        last_10: np.ndarray of shape (10,5) in metric order:
          [T,H,S,L,CO2]
        returns dict with keys in METRICS
        """
        if last_10.shape != (10, 5):
            raise ValueError(f"Expected last_10 shape (10,5), got {last_10.shape}")

        X = last_10.reshape(1, -1)  # (1, 50)
        X_s = self.x_scaler.transform(X)
        y_pred_s = self.model.predict(X_s)  # (1,5)
        y_pred = self.y_scaler.inverse_transform(y_pred_s)[0]

        return {k: float(v) for k, v in zip(METRICS, y_pred)}
