from django.db import models


class GreenhouseReading(models.Model):
    # Timestamp
    timestamp = models.DateTimeField(auto_now_add=True)

    # Sensor readings
    temperature = models.FloatField()
    humidity = models.FloatField()
    soil_moisture = models.FloatField()
    light_intensity = models.FloatField()
    co2_concentration = models.FloatField()

    # Optional: weather & tick info for simulation/testing
    weather = models.CharField(max_length=20, blank=True, null=True)
    tick = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Greenhouse Reading'
        verbose_name_plural = 'Greenhouse Readings'

    def __str__(self):
        return (
            f"Tick {self.tick} | Temp={self.temperature:.2f}°C | "
            f"Humidity={self.humidity:.2f}% | Soil={self.soil_moisture:.2f}% | "
            f"Light={self.light_intensity:.2f}lux | CO2={self.co2_concentration:.2f}ppm"
        )


class GreenhouseCommand(models.Model):
    timestamp = models.DateTimeField(auto_now_add=True)

    heater = models.BooleanField(default=False)
    ventilation = models.BooleanField(default=False)
    irrigation = models.BooleanField(default=False)
    co2_injector = models.BooleanField(default=False)
    lights = models.BooleanField(default=False)
    dehumidifier = models.BooleanField(default=False)
    light_blinds = models.BooleanField(default=False)

    # Optional: tick for simulation
    tick = models.PositiveIntegerField(blank=True, null=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Greenhouse Command'
        verbose_name_plural = 'Greenhouse Commands'

    def __str__(self):
        active = []
        for field in ['heater', 'ventilation', 'irrigation', 'co2_injector', 'lights', 'dehumidifier', 'light_blinds']:
            if getattr(self, field):
                active.append(field)
        return f"Tick {self.tick} | Active: {', '.join(active) if active else 'None'}"


class EquipmentState(models.Model):
    """Tracks current state of each equipment (updated in place)"""
    EQUIPMENT_CHOICES = [
        ('heater', 'Heater'),
        ('ventilation', 'Ventilation'),
        ('irrigation', 'Irrigation'),
        ('co2_injector', 'CO2 Injector'),
        ('lights', 'Lights'),
        ('dehumidifier', 'Dehumidifier'),
        ('light_blinds', 'Light Blinds'),
    ]

    equipment_type = models.CharField(max_length=20, choices=EQUIPMENT_CHOICES, unique=True)
    is_active = models.BooleanField(default=False)
    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Equipment State'
        verbose_name_plural = 'Equipment States'

    def __str__(self):
        status = "ON" if self.is_active else "OFF"
        return f"{self.get_equipment_type_display()}: {status}"