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
            'temperature': -4.0,      # Reduces target by 4°C
            'humidity': -15.0,        # Reduces humidity target
            'co2_concentration': -50.0
        },
        'irrigation': {
            'soil_moisture': +25.0,   # Target much higher moisture
            'humidity': +5.0,
        },
        'co2_injector': {
            'co2_concentration': +400.0  # Target 800ppm
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
    
    def generate_reading(self):
        """Generate the next sensor reading"""
        self.tick += 1
        
        # Check if weather should change (every 10 ticks = 50 seconds)
        if self.tick % 10 == 0:
            self._change_weather()
        
        # Calculate targets and move toward them
        self._move_toward_targets()
        self._constrain_values()
        
        # Create and return reading
        reading = self._create_reading()
        
        return reading
    
    def _change_weather(self):
        """Change weather based on transition rules"""
        possible_weathers = self.WEATHER_TRANSITIONS.get(self.current_weather, ['Clear_sky'])
        new_weather = random.choice(possible_weathers)
        
        print(f"[Tick {self.tick}] Weather changed: {self.current_weather} → {new_weather}")
        self.current_weather = new_weather
    
    def _calculate_target(self, metric):
        """Calculate the target value for a metric based on weather and equipment"""
        # Start with weather target
        target = self.WEATHER_TARGETS[self.current_weather].get(metric, 0)
        
        # Add equipment modifications
        active_equipment = EquipmentState.objects.filter(is_active=True)
        for equipment in active_equipment:
            equipment_mod = self.EQUIPMENT_TARGETS.get(equipment.equipment_type, {})
            target += equipment_mod.get(metric, 0)
        
        return target
    
    def _move_toward_targets(self):
        """Move all metrics toward their target values"""
        # Temperature
        target_temp = self._calculate_target('temperature')
        convergence = self.CONVERGENCE_RATES['temperature']
        self.current_temperature += (target_temp - self.current_temperature) * convergence
        
        # Humidity
        target_humidity = self._calculate_target('humidity')
        convergence = self.CONVERGENCE_RATES['humidity']
        self.current_humidity += (target_humidity - self.current_humidity) * convergence
        
        # Soil Moisture
        target_soil = self._calculate_target('soil_moisture')
        convergence = self.CONVERGENCE_RATES['soil_moisture']
        self.current_soil_moisture += (target_soil - self.current_soil_moisture) * convergence
        
        # Light Intensity
        target_light = self._calculate_target('light_intensity')
        convergence = self.CONVERGENCE_RATES['light_intensity']
        self.current_light_intensity += (target_light - self.current_light_intensity) * convergence
        
        # CO2 Concentration
        target_co2 = self._calculate_target('co2_concentration')
        convergence = self.CONVERGENCE_RATES['co2_concentration']
        self.current_co2_concentration += (target_co2 - self.current_co2_concentration) * convergence
    
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