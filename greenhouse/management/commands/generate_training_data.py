import csv
import random
import time
from pathlib import Path

from django.core.management.base import BaseCommand

from greenhouse.services.data_generator import GreenhouseDataGenerator
from greenhouse.services.decision import GreenhouseDecisionModel
from greenhouse.models import EquipmentState

EQUIPMENT_FIELDS = [
    "heater", "ventilation", "irrigation",
    "co2_injector", "lights", "dehumidifier", "light_blinds"
]


def apply_command_to_equipment_state(command):
    """Closed-loop: apply chosen command to EquipmentState so generator responds next tick."""
    for eq in EQUIPMENT_FIELDS:
        EquipmentState.objects.update_or_create(
            equipment_type=eq,
            defaults={"is_active": bool(getattr(command, eq, False))}
        )


def command_dict(command):
    """Only equipment booleans, no Django internals."""
    return {k: bool(getattr(command, k, False)) for k in EQUIPMENT_FIELDS}


class Command(BaseCommand):
    help = "Generate greenhouse training data (one CSV per run), no split, no weather/tick columns."

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            type=str,
            default="optimal",
            help="Starting configuration name (e.g., optimal, cold_start, hot_humid, random)",
        )
        parser.add_argument(
            "--samples",
            type=int,
            default=1000,
            help="Number of rows to SAVE (command runs samples+1 ticks and drops the first).",
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="Random seed for reproducibility",
        )
        parser.add_argument(
            "--outdir",
            type=str,
            default="datasets",
            help="Output folder (CSV will be saved here)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default=None,
            help="Optional explicit filename. If not provided, auto-named from config/seed/samples.",
        )
        parser.add_argument(
            "--interval",
            type=float,
            default=0.0,
            help="Seconds to wait between ticks (useful for visual testing; keep 0.0 for fast generation).",
        )
        parser.add_argument(
            "--show",
            action="store_true",
            help="Print per-tick readings + commands",
        )

    def handle(self, *args, **options):
        config_name = options["config"]
        samples = options["samples"]
        seed = options["seed"]
        outdir = Path(options["outdir"])
        output = options["output"]
        interval = options["interval"]
        show = options["show"]

        random.seed(seed)

        generator = GreenhouseDataGenerator(config_name=config_name)
        generator.initialize(clear_data=False)
        decision_model = GreenhouseDecisionModel()

        rows = []
        total_steps = samples + 1  # run one extra, drop first

        self.stdout.write(self.style.SUCCESS(
            f"Generating {samples} rows for config='{config_name}' (running {total_steps} ticks, dropping first) ..."
        ))

        for step in range(total_steps):
            reading = generator.generate_reading()
            command = decision_model.decide(reading)

            # Apply command so next tick reflects equipment effects
            apply_command_to_equipment_state(command)

            # Drop first row
            if step == 0:
                if interval > 0:
                    time.sleep(interval)
                continue
            if step%50 == 0:
                print(step)
            cmd = command_dict(command)

            # NOTE: no tick, no weather (as you requested)
            row = {
                "temperature": round(reading.temperature, 2),
                "humidity": round(reading.humidity, 2),
                "soil_moisture": round(reading.soil_moisture, 2),
                "light_intensity": round(reading.light_intensity, 2),
                "co2_concentration": round(reading.co2_concentration, 2),
                **cmd,
            }
            rows.append(row)

            if show:
                on_cmds = [k for k, v in cmd.items() if v]
                self.stdout.write(
                    f"[{config_name}] {step-1:5d} "
                    f"T={row['temperature']:>5.2f} H={row['humidity']:>5.2f} "
                    f"S={row['soil_moisture']:>5.2f} L={row['light_intensity']:>7.0f} "
                    f"CO2={row['co2_concentration']:>6.0f} "
                    f"cmds={','.join(on_cmds) if on_cmds else 'None'}"
                )

            if interval > 0:
                time.sleep(interval)

        outdir.mkdir(parents=True, exist_ok=True)

        if output is None:
            ts = time.strftime("%Y%m%d-%H%M%S")
            output = f"{config_name}_samples{samples}_seed{seed}_{ts}.csv"

        outpath = outdir / output

        # Write CSV
        fieldnames = list(rows[0].keys()) if rows else []
        with outpath.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        self.stdout.write(self.style.SUCCESS(f"Saved {len(rows)} rows to: {outpath}"))


# optimal: 2000

# random: 2000

# cold_start: 1200

# hot_humid: 1200

# night_cold: 900

# heat_stress: 900

# mold_risk: 900

# drought: 700

# conflict_start: 200

# sensor_glitch: 100