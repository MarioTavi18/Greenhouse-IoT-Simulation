from __future__ import annotations

import time
import threading
from collections import deque

import numpy as np
from django.db import transaction

from greenhouse.models import EquipmentState, GreenhouseCommand, GreenhouseReading
from greenhouse.services.data_generator import GreenhouseDataGenerator
from greenhouse.services.ml.ridge_predictor import RidgeNextTickPredictor
from greenhouse.services.ml.rf_command_model import RFCommandModel, EQUIPMENT

METRICS = ["temperature", "humidity", "soil_moisture", "light_intensity", "co2_concentration"]


def get_equipment_state_dict() -> dict:
    return {e.equipment_type: bool(e.is_active) for e in EquipmentState.objects.all()}


def apply_equipment_state(new_state: dict):
    for eq in EQUIPMENT:
        EquipmentState.objects.update_or_create(
            equipment_type=eq,
            defaults={"is_active": bool(new_state.get(eq, False))}
        )


class SimulationRunner:
    """
    Single-process demo runner:
      - background thread
      - loop generates readings at interval seconds
      - every 10 ticks: call ridge predictor with last 10 readings
      - feed predicted metrics + current equipment state to RF command model
      - persist command, update equipment state
    """

    def __init__(self):
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

        self.is_running = False
        self.tick = 0
        self.config_name = None
        self.interval = 1.0

        self.generator: GreenhouseDataGenerator | None = None
        self.predictor = RidgeNextTickPredictor("trained_models/ridge_next_tick.joblib")
        self.controller = RFCommandModel("trained_models")

        # store last 10 readings (T,H,S,L,CO2)
        self.last10 = deque(maxlen=10)

    def start(self, config_name: str = "optimal", interval: float = 1.0, clear_data: bool = False):
        if self.is_running:
            return

        self.config_name = config_name
        self.interval = float(interval)
        self.tick = 0
        self.last10.clear()
        self._stop_event.clear()

        self.generator = GreenhouseDataGenerator(config_name=config_name)
        self.generator.initialize(clear_data=clear_data)

        # Prime the deque from DB with the most recent reading if available
        latest = GreenhouseReading.objects.order_by("-id").first()
        if latest:
            self.last10.append([latest.temperature, latest.humidity, latest.soil_moisture, latest.light_intensity, latest.co2_concentration])

        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self.is_running = True
        self._thread.start()

    def stop(self):
        if not self.is_running:
            return
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        self.is_running = False

    def status(self) -> dict:
        return {
            "running": self.is_running,
            "tick": self.tick,
            "config": self.config_name,
            "interval": self.interval,
            "last10_len": len(self.last10),
        }

    def _run_loop(self):
        while not self._stop_event.is_set():
            try:
                self._one_tick()
            except Exception as e:
                # for demo purposes; in real systems you'd log properly
                print(f"[SimulationRunner] ERROR at tick {self.tick}: {e}")

            if self.interval > 0:
                time.sleep(self.interval)

        self.is_running = False

    @transaction.atomic
    def _one_tick(self):
        assert self.generator is not None

        # 1) Generate + save a new reading (your generator already saves it)
        reading = self.generator.generate_reading()
        self.tick += 1

        # Push to last10
        self.last10.append([reading.temperature, reading.humidity, reading.soil_moisture, reading.light_intensity, reading.co2_concentration])

        # 2) Decide command
        # If we don't have 10 readings yet, just keep current equipment state (warm-up)
        equipment_now = get_equipment_state_dict()
        prev_features = {f"prev_{k}": int(bool(equipment_now.get(k, False))) for k in EQUIPMENT}

        if len(self.last10) < 10:
            cmd_dict = equipment_now  # keep state during warmup
        else:
            # Every 10 ticks, run ridge predictor.
            # Between those calls, reuse the last prediction (stable) or you can still predict every tick.
            # Here: we predict only when tick%10==0, otherwise reuse last predicted values from last call.
            if self.tick % 10 == 0 or not hasattr(self, "_cached_pred"):
                last_10_np = np.array(self.last10, dtype=float)  # (10,5)
                self._cached_pred = self.predictor.predict_next(last_10_np)

            pred = self._cached_pred  # dict of 5 metrics

            features = {
                "temperature": pred["temperature"],
                "humidity": pred["humidity"],
                "soil_moisture": pred["soil_moisture"],
                "light_intensity": pred["light_intensity"],
                "co2_concentration": pred["co2_concentration"],
                **prev_features,
            }

            cmd_dict = self.controller.decide(features)

        # 3) Persist command + update EquipmentState
        GreenhouseCommand.objects.create(
            heater=bool(cmd_dict.get("heater", False)),
            ventilation=bool(cmd_dict.get("ventilation", False)),
            irrigation=bool(cmd_dict.get("irrigation", False)),
            co2_injector=bool(cmd_dict.get("co2_injector", False)),
            lights=bool(cmd_dict.get("lights", False)),
            dehumidifier=bool(cmd_dict.get("dehumidifier", False)),
            light_blinds=bool(cmd_dict.get("light_blinds", False)),
        )

        apply_equipment_state(cmd_dict)
