import random
from greenhouse.models import GreenhouseReading, EquipmentState

class GreenhouseDataGenerator:
    """Generates realistic greenhouse sensor readings with equilibrium targets"""
    
    # Weather target states (what conditions naturally settle at)
    WEATHER_TARGETS = {
        'Sunny': {
            'temperature': 28.0,      # Hot in sun
            'humidity': 45.0,         # Dry in sun
            'light_intensity': 35000, # Bright sunlight
            'soil_moisture': 50.0,    # Evaporates
            'co2_concentration': 400.0
        },
        'Clear_sky': {
            'temperature': 23.0,      # Mild
            'humidity': 60.0,         # Moderate
            'light_intensity': 15000, # Good light
            'soil_moisture': 55.0,
            'co2_concentration': 400.0
        },
        'Cloudy': {
            'temperature': 19.0,      # Cool
            'humidity': 75.0,         # Humid
            'light_intensity': 5000,  # Dim
            'soil_moisture': 58.0,
            'co2_concentration': 400.0
        },
        'Rainy': {
            'temperature': 16.0,      # Cold
            'humidity': 90.0,         # Very humid
            'light_intensity': 2000,  # Dark
            'soil_moisture': 75.0,    # Wet
            'co2_concentration': 400.0
        },
        'Windy': {
            'temperature': 20.0,      # Cool from wind
            'humidity': 50.0,         # Dry from wind
            'light_intensity': 12000, # Variable
            'soil_moisture': 48.0,    # Dries fast
            'co2_concentration': 380.0 # Ventilated
        }
    }
    
    # Equipment target modifications (added to weather targets when active)
    EQUIPMENT_TARGETS = {
        'heater': {
            'temperature': +8.0,      # Adds 8°C to target
        },
        'ventilation': {
            'temperature': -8.0,      # Reduces target by 8°C
            'humidity': -15.0,        # Reduces humidity target
            'co2_concentration': -50.0
        },
        'irrigation': {
            'soil_moisture': +25.0,   # Target much higher moisture
            'humidity': +5.0,
        },
        'co2_injector': {
            'co2_concentration': +300.0  # Target 300ppm
        },
        'lights': {
            'light_intensity': +15000,   # Add artificial light target
            'temperature': +2.0,
        },
        'dehumidifier': {
            'humidity': -20.0,        # Target lower humidity
            'temperature': +1.5,      # Dehumidifiers warm slightly
        },
        'light_blinds': {
            'light_intensity': -10000,   # Reduce light significantly
        }
    }
    
    # Convergence rates (how fast values move toward targets)
    # Higher = faster convergence, Lower = slower/smoother
    CONVERGENCE_RATES = {
        'temperature': 0.08,       # Moderate temperature change
        'humidity': 0.10,          # Humidity changes fairly quick
        'soil_moisture': 0.05,     # Soil changes slowly
        'light_intensity': 0.15,   # Light changes quickly
        'co2_concentration': 0.12, # CO2 changes moderately
    }
    
    # Weather transitions
    WEATHER_TRANSITIONS = {
        'Sunny': ['Cloudy', 'Clear_sky', 'Windy'],
        'Clear_sky': ['Cloudy', 'Sunny', 'Windy'],
        'Cloudy': ['Sunny', 'Clear_sky', 'Rainy', 'Windy'],
        'Rainy': ['Cloudy','Windy'],
        'Windy': ['Cloudy', 'Clear_sky','Rainy']
    }
    
    # Starting configurations
    STARTING_CONFIGS = {
        'optimal': {
            'temperature': 22.0,
            'humidity': 65.0,
            'soil_moisture': 60.0,
            'light_intensity': 5000.0,
            'co2_concentration': 400.0,
            'weather': 'Clear_sky',
            'equipment': {
                'heater': False,
                'ventilation': False,
                'irrigation': False,
                'co2_injector': False,
                'lights': False,
                'dehumidifier': False,
                'light_blinds': False,
            }
        },
        'cold_start': {
            'temperature': 15.0,
            'humidity': 80.0,
            'soil_moisture': 45.0,
            'light_intensity': 1000.0,
            'co2_concentration': 350.0,
            'weather': 'Cloudy',
            'equipment': {
                'heater': True,
                'ventilation': False,
                'irrigation': True,
                'co2_injector': False,
                'lights': True,
                'dehumidifier': False,
                'light_blinds': False,
            }
        },
        'hot_humid': {
            'temperature': 30.0,
            'humidity': 85.0,
            'soil_moisture': 70.0,
            'light_intensity': 8000.0,
            'co2_concentration': 450.0,
            'weather': 'Sunny',
            'equipment': {
                'heater': False,
                'ventilation': True,
                'irrigation': False,
                'co2_injector': False,
                'lights': False,
                'dehumidifier': True,
                'light_blinds': False,
            }
        },
        'random': {
            'temperature': lambda: random.uniform(18.0, 28.0),
            'humidity': lambda: random.uniform(50.0, 80.0),
            'soil_moisture': lambda: random.uniform(40.0, 70.0),
            'light_intensity': lambda: random.uniform(2000.0, 8000.0),
            'co2_concentration': lambda: random.uniform(350.0, 500.0),
            'weather': lambda: random.choice(['Sunny', 'Clear_sky', 'Cloudy', 'Rainy', 'Windy']),
            'equipment': {
                'heater': lambda: random.choice([True, False]),
                'ventilation': lambda: random.choice([True, False]),
                'irrigation': lambda: random.choice([True, False]),
                'co2_injector': lambda: random.choice([True, False]),
                'lights': lambda: random.choice([True, False]),
                'dehumidifier': lambda: random.choice([True, False]),
                'light_blinds': lambda: random.choice([True, False]),
            }
        },
            'night_cold': {
            'temperature': 14.0,
            'humidity': 70.0,
            'soil_moisture': 55.0,
            'light_intensity': 300.0,
            'co2_concentration': 420.0,
            'weather': 'Clear_sky',
            'equipment': {
                'heater': False, 'ventilation': False, 'irrigation': False,
                'co2_injector': False, 'lights': False, 'dehumidifier': False, 'light_blinds': False,
            }
        },
        'heat_stress': {
            'temperature': 38.0,
            'humidity': 40.0,
            'soil_moisture': 45.0,
            'light_intensity': 60000.0,
            'co2_concentration': 430.0,
            'weather': 'Sunny',
            'equipment': {
                'heater': False, 'ventilation': False, 'irrigation': False,
                'co2_injector': False, 'lights': True, 'dehumidifier': False, 'light_blinds': False,
            }
        },
        'mold_risk': {
        'temperature': 18.0,
        'humidity': 95.0,
        'soil_moisture': 70.0,
        'light_intensity': 4000.0,
        'co2_concentration': 420.0,
        'weather': 'Rainy',
        'equipment': {
            'heater': False, 'ventilation': False, 'irrigation': True,
            'co2_injector': False, 'lights': False, 'dehumidifier': False, 'light_blinds': False,
            }
        },
        'drought': {
        'temperature': 26.0,
        'humidity': 35.0,
        'soil_moisture': 10.0,
        'light_intensity': 12000.0,
        'co2_concentration': 420.0,
        'weather': 'Windy',
        'equipment': {
            'heater': False, 'ventilation': False, 'irrigation': False,
            'co2_injector': False, 'lights': False, 'dehumidifier': False, 'light_blinds': False,
            }
        },
        'sensor_glitch': {
        'temperature': 0.0,
        'humidity': 0.0,
        'soil_moisture': 0.0,
        'light_intensity': 0.0,
        'co2_concentration': 2000.0,
        'weather': 'Clear_sky',
        'equipment': {
            'heater': False, 'ventilation': False, 'irrigation': False,
            'co2_injector': True, 'lights': True, 'dehumidifier': True, 'light_blinds': False,
            }
        },
        'conflict_start': {
        'temperature': 22.0,
        'humidity': 65.0,
        'soil_moisture': 55.0,
        'light_intensity': 7000.0,
        'co2_concentration': 450.0,
        'weather': 'Clear_sky',
        'equipment': {
            'heater': True,
            'ventilation': True,   # conflict
            'irrigation': False,
            'co2_injector': True,
            'lights': True,
            'dehumidifier': True,
            'light_blinds': True,  # conflict vs lights
            }
        }

    }
    
    def __init__(self, config_name='optimal'):
        """Initialize with a starting configuration"""
        self.config_name = config_name
        self.tick = 0
        self.current_weather = None
        
        # Current state values (will be set by initialize())
        self.current_temperature = None
        self.current_humidity = None
        self.current_soil_moisture = None
        self.current_light_intensity = None
        self.current_co2_concentration = None

                # Last computed targets (for logging/debug)
        self.last_targets = {}

    
    def initialize(self, clear_data=True):
        """Initialize the simulation"""
        if clear_data:
            # Clear all previous data
            GreenhouseReading.objects.all().delete()
            print(f"Cleared all previous readings")
        
        # Get starting config
        config = self.STARTING_CONFIGS.get(self.config_name, self.STARTING_CONFIGS['optimal'])
        
        # Set initial values (handle random config)
        self.current_temperature = config['temperature']() if callable(config['temperature']) else config['temperature']
        self.current_humidity = config['humidity']() if callable(config['humidity']) else config['humidity']
        self.current_soil_moisture = config['soil_moisture']() if callable(config['soil_moisture']) else config['soil_moisture']
        self.current_light_intensity = config['light_intensity']() if callable(config['light_intensity']) else config['light_intensity']
        self.current_co2_concentration = config['co2_concentration']() if callable(config['co2_concentration']) else config['co2_concentration']
        self.current_weather = config['weather']() if callable(config['weather']) else config['weather']
        
        # Initialize equipment states
        self._initialize_equipment(config['equipment'])
        
        # Create first reading
        first_reading = self._create_reading()
        
        print(f"Initialized with config: {self.config_name}")
        print(f"Starting weather: {self.current_weather}")
        print(f"Starting conditions: T={self.current_temperature:.1f}°C, H={self.current_humidity:.1f}%, S={self.current_soil_moisture:.1f}%")
        
        return first_reading
    
    def _compute_targets(self):
        """Compute all metric targets for the current tick (weather + equipment)."""
        metrics = [
            "temperature",
            "humidity",
            "soil_moisture",
            "light_intensity",
            "co2_concentration",
        ]
        return {m: self._calculate_target(m) for m in metrics}


    def _initialize_equipment(self, equipment_config):
        """Initialize or reset equipment states"""
        for equipment_type, is_active in equipment_config.items():
            active = is_active() if callable(is_active) else is_active
            
            equipment, created = EquipmentState.objects.get_or_create(
                equipment_type=equipment_type,
                defaults={'is_active': active}
            )
            
            if not created:
                equipment.is_active = active
                equipment.save()
    
    def generate_reading(self, show_targets: bool = False):
        """Generate the next sensor reading"""
        self.tick += 1

        # Check if weather should change
        if self.tick % 40 == 0:
            self._change_weather()

        # NEW: calculate all targets once per tick (and reuse)
        targets = self._calculate_targets()
        self.last_targets = targets

        # Move toward targets
        self._move_toward_targets(targets)
        self._constrain_values()

        # Create and return reading
        reading = self._create_reading()

        # OPTIONAL: print targets each tick
        if show_targets:
            self._print_tick_debug(reading, targets)

        return reading

    # ---------- NEW helpers ----------

    def _calculate_targets(self):
        """Calculate targets for all metrics based on weather + currently active equipment."""
        # Start with weather targets
        targets = dict(self.WEATHER_TARGETS[self.current_weather])

        # Add equipment modifications (query active equipment ONCE)
        active_equipment = EquipmentState.objects.filter(is_active=True)
        for equipment in active_equipment:
            equipment_mod = self.EQUIPMENT_TARGETS.get(equipment.equipment_type, {})
            for metric, delta in equipment_mod.items():
                targets[metric] = targets.get(metric, 0) + delta

        return targets

    def _print_tick_debug(self, reading: GreenhouseReading, targets: dict):
        """Pretty debug output for current values + targets."""
        print(
            f"[TARGET |"
            f"CUR:  T={reading.temperature:5.2f}°C  H={reading.humidity:5.2f}%  "
            f"S={reading.soil_moisture:5.2f}%  L={reading.light_intensity:7.0f}lx  "
            f"CO2={reading.co2_concentration:6.0f}ppm | "
            f"TGT:  T={targets['temperature']:5.2f}°C  H={targets['humidity']:5.2f}%  "
            f"S={targets['soil_moisture']:5.2f}%  L={targets['light_intensity']:7.0f}lx  "
            f"CO2={targets['co2_concentration']:6.0f}ppm"
        )

    # ---------- UPDATED move_toward_targets ----------

    def _move_toward_targets(self, targets: dict):
        """Move all metrics toward their target values"""

        # Temperature
        convergence = self.CONVERGENCE_RATES['temperature']
        self.current_temperature += (targets['temperature'] - self.current_temperature) * convergence

        # Humidity
        convergence = self.CONVERGENCE_RATES['humidity']
        self.current_humidity += (targets['humidity'] - self.current_humidity) * convergence

        # Soil Moisture
        convergence = self.CONVERGENCE_RATES['soil_moisture']
        self.current_soil_moisture += (targets['soil_moisture'] - self.current_soil_moisture) * convergence

        # Light Intensity
        convergence = self.CONVERGENCE_RATES['light_intensity']
        self.current_light_intensity += (targets['light_intensity'] - self.current_light_intensity) * convergence

        # CO2 Concentration
        convergence = self.CONVERGENCE_RATES['co2_concentration']
        self.current_co2_concentration += (targets['co2_concentration'] - self.current_co2_concentration) * convergence

    
    def _change_weather(self):
        """Change weather based on transition rules"""
        possible_weathers = self.WEATHER_TRANSITIONS.get(self.current_weather, ['Clear_sky'])
        new_weather = random.choice(possible_weathers)
        
        print(f"[Tick {self.tick}] Weather changed: {self.current_weather} → {new_weather}")
        self.current_weather = new_weather
    
    # def _calculate_target(self, metric):
    #     """Calculate the target value for a metric based on weather and equipment"""
    #     # Start with weather target
    #     target = self.WEATHER_TARGETS[self.current_weather].get(metric, 0)
        
    #     # Add equipment modifications
    #     active_equipment = EquipmentState.objects.filter(is_active=True)
    #     for equipment in active_equipment:
    #         equipment_mod = self.EQUIPMENT_TARGETS.get(equipment.equipment_type, {})
    #         target += equipment_mod.get(metric, 0)
    #     return target
    
    
    def _constrain_values(self):
        """Keep values within realistic bounds"""
        self.current_temperature = max(0, min(50, self.current_temperature))
        self.current_humidity = max(0, min(100, self.current_humidity))
        self.current_soil_moisture = max(0, min(100, self.current_soil_moisture))
        self.current_light_intensity = max(0, min(100000, self.current_light_intensity))
        self.current_co2_concentration = max(300, min(2000, self.current_co2_concentration))
    
    def _add_noise(self, value, noise_percent=1.0):
        """Add realistic sensor noise"""
        noise = value * (noise_percent / 100.0)
        return value + random.uniform(-noise, noise)
    
    def _create_reading(self):
        """Create and save a greenhouse reading"""
        reading = GreenhouseReading.objects.create(
            temperature=self._add_noise(self.current_temperature, 0.5),
            humidity=self._add_noise(self.current_humidity, 1.0),
            soil_moisture=self._add_noise(self.current_soil_moisture, 1.5),
            light_intensity=self._add_noise(self.current_light_intensity, 2.0),
            co2_concentration=self._add_noise(self.current_co2_concentration, 1.0),
            weather=self.current_weather,
            tick=self.tick
        )
        
        return reading