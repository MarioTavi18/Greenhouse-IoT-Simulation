from dataclasses import dataclass
from greenhouse.models import GreenhouseReading, GreenhouseCommand


@dataclass
class GreenhouseThresholds:
    """Configuration thresholds for the decision tree"""
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
    CO2_MIN: float = 800.0
    CO2_BUFFER: float = 50.0

    # Light (lux)
    LIGHT_MIN_GROWTH: float = 5000.0
    LIGHT_MAX_STRESS: float = 50000.0


class GreenhouseDecisionModel:
    """A decision tree model that accepts a predicted GreenhouseReading and returns the optimal GreenhouseCommand"""

    def __init__(self, config: GreenhouseThresholds = None):
        self.config = config if config else GreenhouseThresholds()

    def decide(self, prediction: GreenhouseReading) -> GreenhouseCommand:
        """Main entry point for the decision tree"""

        # Initialize command with all systems OFF
        command = GreenhouseCommand()

        # Get the last command from the database
        last_command = GreenhouseCommand.objects.last()

        # Decision 1: Temperature (Root Node)
        self._evaluate_temperature(prediction, command, last_command)

        # Decision 2: Humidity
        # This is evaluated after Temp because Vents affect humidity
        self._evaluate_humidity(prediction, command, last_command)

        # Decision 3: Soil moisture
        self._evaluate_soil_moisture(prediction, command)

        # Decision 4: Lighting
        self._evaluate_light_intensity(prediction, command, last_command)

        # Decision 5: CO2
        self._evaluate_co2_concentration(prediction, command)

        return command


    def _evaluate_temperature(self, prediction: GreenhouseReading, command: GreenhouseCommand, equipment_state: GreenhouseCommand):
        """Decision Logic for Temperature"""

        # Heater logic
        if prediction.temperature < self.config.TEMP_MIN:
            command.heater = True

        elif equipment_state and equipment_state.heater:
            # We are currently heating.
            # Only stop heating if we are safely above the minimum
            if prediction.temperature > self.config.TEMP_MIN + self.config.TEMP_BUFFER:
                command.heater = False
            else:
                command.heater = True

        else:
            command.heater = False

        # Ventilation logic
        if prediction.temperature > self.config.TEMP_MAX:
            command.ventilation = True

        elif equipment_state and equipment_state.ventilation:
            # We are currently venting
            # Only stop venting if we are safely below the maximum
            if prediction.temperature < self.config.TEMP_MAX - self.config.TEMP_BUFFER:
                command.ventilation = False
            else:
                command.ventilation = True

        else:
            command.ventilation = False


    def _evaluate_humidity(self, prediction: GreenhouseReading, command: GreenhouseCommand, equipment_state: GreenhouseCommand):
        """Decision Logic for Humidity"""

        if prediction.humidity > self.config.HUM_MAX:
            # High Humidity
            # If ventilation is already on for temperature,it helps with humidity too
            if not command.ventilation:
                # If ventilation is off, we use the dehumidifier to avoid losing heat
                command.dehumidifier = True

        elif prediction.humidity < self.config.HUM_MIN:
            # Low Humidity
            command.dehumidifier = False

        elif equipment_state and equipment_state.dehumidifier:
            # Only stop the dehumidifier if the humidity is safely below the maximum
            if prediction.humidity < self.config.HUM_MAX - self.config.HUM_BUFFER:
                command.dehumidifier = False
            else:
                command.dehumidifier = True

        else:
            command.dehumidifier = False


    def _evaluate_soil_moisture(self, prediction: GreenhouseReading, command: GreenhouseCommand, equipment_state: GreenhouseCommand):
        """Decision Logic for Soil Moisture"""

        if prediction.soil_moisture < self.config.SOIL_MIN:
            command.irrigation = True

        elif equipment_state and equipment_state.irrigation:
            # Only stop irrigation if the soil moisture is safely above the minimum
            if prediction.soil_moisture > self.config.SOIL_MIN + self.config.SOIL_BUFFER:
                command.irrigation = False

        else:
            command.irrigation = False


    def _evaluate_light_intensity(self, prediction: GreenhouseReading, command: GreenhouseCommand, equipment_state: GreenhouseCommand):
        """Decision Logic for Lighting"""

        if prediction.light_intensity < self.config.LIGHT_MIN_GROWTH:
            # Too dark
            command.light_blinds = False
            if equipment_state and not equipment_state.light_blinds:
                command.lights = True

        elif prediction.light_intensity > self.config.LIGHT_MAX_STRESS:
            # Too bright
            command.lights = False
            if equipment_state and not equipment_state.lights:
                command.light_blinds = True

        else:
            # Optimal light
            command.lights = equipment_state.lights
            command.light_blinds = equipment_state.light_blinds


    def _evaluate_co2_concentration(self, prediction: GreenhouseReading, command: GreenhouseCommand, equipment_state: GreenhouseCommand):
        """Decision Logic for CO2"""

        if prediction.co2_concentration < self.config.CO2_MIN:
            command.co2_injector = True

        elif equipment_state and equipment_state.co2_injector:
            # Only stop the CO2 injector if the CO2 concentration is safely above the minimum
            if prediction.co2_concentration > self.config.CO2_MIN + self.config.CO2_BUFFER:
                command.co2_injector = False

        else:
            command.co2_injector = False
