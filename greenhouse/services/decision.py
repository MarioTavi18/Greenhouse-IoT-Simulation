from dataclasses import dataclass
from greenhouse.models import GreenhouseReading, GreenhouseCommand, EquipmentState


@dataclass
class GreenhouseThresholds:
    # Temperature (Celsius)
    TEMP_MIN: float = 20.0
    TEMP_MAX: float = 25.0
    TEMP_BUFFER: float = 1.5

    # Humidity (%)
    HUM_MIN: float = 50.0
    HUM_MAX: float = 80.0
    HUM_BUFFER: float = 5.0

    # Soil Moisture (%)
    SOIL_MIN: float = 40.0
    SOIL_BUFFER: float = 5.0

    # CO2 (ppm)
    CO2_MIN: float = 450.0
    CO2_BUFFER: float = 50.0

    # Light (lux)
    LIGHT_MIN_GROWTH: float = 5000.0
    LIGHT_MAX_STRESS: float = 50000.0


class GreenhouseDecisionModel:
    """
    Rule-based controller that:
      - Uses EquipmentState (DB) as the source of truth
      - Applies hysteresis (buffers)
      - Resolves cross-effects between equipments (ventilation vs CO2, irrigation vs humidity, lights vs temperature, etc.)
    """

    def __init__(self, config: GreenhouseThresholds | None = None):
        self.config = config if config else GreenhouseThresholds()

    def decide(self, prediction: GreenhouseReading) -> GreenhouseCommand:
        # ---- Read current equipment state (source of truth) ----
        equipment_state = {
            e.equipment_type: e.is_active for e in EquipmentState.objects.all()
        }

        # Helper to safely read current state
        def is_on(name: str) -> bool:
            return bool(equipment_state.get(name, False))

        # ---- Start from "keep current state" (good for stability) ----
        cmd = GreenhouseCommand(
            heater=is_on("heater"),
            ventilation=is_on("ventilation"),
            irrigation=is_on("irrigation"),
            co2_injector=is_on("co2_injector"),
            lights=is_on("lights"),
            dehumidifier=is_on("dehumidifier"),
            light_blinds=is_on("light_blinds"),
        )

        # ============================================================
        # 1) TEMPERATURE CONTROL (safety-ish priority)
        # ============================================================
        # Heater: turn on if below min; if on, turn off only above min+buffer
        if prediction.temperature < self.config.TEMP_MIN:
            cmd.heater = True
        elif is_on("heater"):
            cmd.heater = prediction.temperature <= (self.config.TEMP_MIN + self.config.TEMP_BUFFER)
        else:
            cmd.heater = False

        # Ventilation: turn on if above max; if on, turn off only below max-buffer
        if prediction.temperature > self.config.TEMP_MAX:
            cmd.ventilation = True
        elif is_on("ventilation"):
            cmd.ventilation = prediction.temperature >= (self.config.TEMP_MAX - self.config.TEMP_BUFFER)
        else:
            cmd.ventilation = False

        # Conflict: don't heat and ventilate at the same time (wastes energy)
        # If both would be True, prefer ventilation when overheating, else heater.
        if cmd.heater and cmd.ventilation:
            if prediction.temperature > self.config.TEMP_MAX:
                cmd.heater = False
            else:
                cmd.ventilation = False

        # ============================================================
        # 2) LIGHT CONTROL (depends on temperature)
        # ============================================================
        # Too bright -> use blinds
        if prediction.light_intensity > self.config.LIGHT_MAX_STRESS:
            cmd.light_blinds = True
            cmd.lights = False  # don't add more light

        # Too dark -> use lights, but avoid if we're overheating
        elif prediction.light_intensity < self.config.LIGHT_MIN_GROWTH:
            cmd.light_blinds = False
            # If near/above max temp, don't force lights (they add heat in your generator)
            if prediction.temperature >= (self.config.TEMP_MAX - 0.5):
                cmd.lights = False
            else:
                cmd.lights = True

        # Optimal band -> keep current (already initialized)
        else:
            cmd.lights = is_on("lights")
            cmd.light_blinds = is_on("light_blinds")

        # ============================================================
        # 3) HUMIDITY CONTROL (ventilation affects humidity)
        # ============================================================
        # If humidity too high:
        #   - Prefer ventilation if it won't cause under-temp
        #   - Else use dehumidifier
        if prediction.humidity > self.config.HUM_MAX:
            if prediction.temperature > (self.config.TEMP_MIN + 0.5):
                cmd.ventilation = True
                cmd.dehumidifier = False
            else:
                cmd.dehumidifier = True

        # If humidity too low: dehumidifier off
        elif prediction.humidity < self.config.HUM_MIN:
            cmd.dehumidifier = False

        # Hysteresis for dehumidifier if currently on
        elif is_on("dehumidifier"):
            # keep it on until safely below HUM_MAX - buffer
            cmd.dehumidifier = prediction.humidity >= (self.config.HUM_MAX - self.config.HUM_BUFFER)
        else:
            cmd.dehumidifier = False

        # ============================================================
        # 4) SOIL MOISTURE CONTROL (irrigation increases humidity in your generator)
        # ============================================================
        # If soil is too dry -> irrigate, unless humidity already too high
        if prediction.soil_moisture < self.config.SOIL_MIN:
            if prediction.humidity > (self.config.HUM_MAX - 2.0):
                cmd.irrigation = False
            else:
                cmd.irrigation = True

        # Hysteresis if currently irrigating: stop only above SOIL_MIN + buffer
        elif is_on("irrigation"):
            cmd.irrigation = prediction.soil_moisture <= (self.config.SOIL_MIN + self.config.SOIL_BUFFER)
        else:
            cmd.irrigation = False

        # ============================================================
        # 5) CO2 CONTROL (ventilation lowers CO2 in your generator)
        # ============================================================
        # If ventilation is on, don't inject CO2 (otherwise you're "fighting yourself").
        if cmd.ventilation:
            cmd.co2_injector = False
        else:
            # Turn on if below min; if on, turn off only above min+buffer
            if prediction.co2_concentration < self.config.CO2_MIN:
                cmd.co2_injector = True
            elif is_on("co2_injector"):
                cmd.co2_injector = prediction.co2_concentration <= (self.config.CO2_MIN + self.config.CO2_BUFFER)
            else:
                cmd.co2_injector = False

        # ============================================================
        # FINAL CONFLICT RESOLUTION PASS (small but important)
        # ============================================================
        # If we’re ventilating to cool/dry, avoid adding heat sources if not necessary.
        if cmd.ventilation and prediction.temperature >= self.config.TEMP_MAX:
            cmd.lights = False  # lights add heat in your generator
            # dehumidifier generally unnecessary if ventilation is already running
            cmd.dehumidifier = False

        # If we’re heating because it's cold, avoid ventilation unless humidity is dangerously high.
        if cmd.heater and prediction.temperature <= self.config.TEMP_MIN:
            if prediction.humidity <= (self.config.HUM_MAX + 5.0):
                cmd.ventilation = False

        return cmd
