from django.core.management.base import BaseCommand
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.utils import timezone
from greenhouse.services.data_generator import GreenhouseDataGenerator
from greenhouse.models import EquipmentState
import sys

class Command(BaseCommand):
    help = 'Runs the greenhouse simulation with continuous data generation'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--config',
            type=str,
            default='optimal',
            choices=['optimal', 'cold_start', 'hot_humid', 'random'],
            help='Starting configuration (default: optimal)'
        )
        parser.add_argument(
            '--continue',
            action='store_true',
            help='Continue from last state without clearing data'
        )
        parser.add_argument(
            '--interval',
            type=float,
            default=5,
            help='Data generation interval in seconds (default: 5)'
        )
    
    def handle(self, *args, **options):
        config = options['config']
        continue_simulation = options['continue']
        interval = options['interval']
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(self.style.SUCCESS('  GREENHOUSE SIMULATION STARTING'))
        self.stdout.write(self.style.SUCCESS('=' * 60))
        self.stdout.write(f'Configuration: {config}')
        self.stdout.write(f'Data generation: every {interval} seconds')
        self.stdout.write(f'Weather changes: every 10 ticks ({interval * 10} seconds)')
        
        if continue_simulation:
            self.stdout.write(self.style.WARNING('Continuing from last state (data preserved)'))
        else:
            self.stdout.write(self.style.WARNING('Starting fresh (clearing all previous data)'))
        
        self.stdout.write(self.style.SUCCESS('=' * 60))
        
        # Initialize data generator
        generator = GreenhouseDataGenerator(config_name=config)
        
        # Initialize (clear data unless continuing)
        first_reading = generator.initialize(clear_data=not continue_simulation)
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Simulation initialized'))
        self.stdout.write(f'  Tick: {first_reading.tick}')
        self.stdout.write(f'  Weather: {first_reading.weather}')
        self.stdout.write(f'  Temperature: {first_reading.temperature:.1f}°C')
        self.stdout.write(f'  Humidity: {first_reading.humidity:.1f}%')
        self.stdout.write(f'  Soil Moisture: {first_reading.soil_moisture:.1f}%')
        self.stdout.write(f'  Light: {first_reading.light_intensity:.0f} lux')
        self.stdout.write(f'  CO2: {first_reading.co2_concentration:.0f} ppm')
        
        # Show equipment status
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('✓ Equipment Status:'))
        equipment_states = EquipmentState.objects.all().order_by('equipment_type')
        for equipment in equipment_states:
            status = self.style.SUCCESS('ON ') if equipment.is_active else self.style.ERROR('OFF')
            self.stdout.write(f'  {equipment.get_equipment_type_display():15s}: {status}')
        
        self.stdout.write('')
        self.stdout.write(self.style.SUCCESS('Simulation running... Press Ctrl+C to stop'))
        self.stdout.write('-' * 60)
        
        # Create scheduler
        scheduler = BlockingScheduler()
        
        # Schedule data generation
        scheduler.add_job(
            func=self.generate_data,
            trigger=IntervalTrigger(seconds=interval),
            args=[generator],
            id='data_generation',
            name='Generate sensor readings',
            replace_existing=True
        )
        
        try:
            scheduler.start()
        except KeyboardInterrupt:
            self.stdout.write('')
            self.stdout.write('-' * 60)
            self.stdout.write(self.style.WARNING('Stopping simulation...'))
            scheduler.shutdown()
            
            # Show final stats
            from greenhouse.models import GreenhouseReading
            total_readings = GreenhouseReading.objects.count()
            last_reading = GreenhouseReading.objects.first()
            
            self.stdout.write('')
            self.stdout.write(self.style.SUCCESS('Simulation stopped'))
            self.stdout.write(f'Total readings generated: {total_readings}')
            if last_reading:
                self.stdout.write(f'Last tick: {last_reading.tick}')
                self.stdout.write(f'Duration: ~{last_reading.tick * interval} seconds')
            self.stdout.write('')
    
    def generate_data(self, generator):
        """Generate and store sensor reading"""
        try:
            reading = generator.generate_reading()
            
            # Format output
            timestamp = timezone.now().strftime("%H:%M:%S")
            
            # Show every reading
            output = (
                f'[{timestamp}] Tick {reading.tick:3d} | '
                f'{reading.weather:10s} | '
                f'T={reading.temperature:5.1f}°C | '
                f'H={reading.humidity:5.1f}% | '
                f'S={reading.soil_moisture:5.1f}% | '
                f'L={reading.light_intensity:6.0f}lux | '
                f'CO2={reading.co2_concentration:4.0f}ppm'
            )
            
            self.stdout.write(output)
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error generating data: {e}'))
            import traceback
            traceback.print_exc()