import argparse
from pathlib import Path

import pandas as pd

EQUIPMENT_FIELDS = [
    "heater", "ventilation", "irrigation",
    "co2_injector", "lights", "dehumidifier", "light_blinds"
]

READING_FIELDS = [
    "temperature", "humidity", "soil_moisture", "light_intensity", "co2_concentration"
]


def convert_file(in_path: Path, out_path: Path, drop_first: bool) -> None:
    df = pd.read_csv(in_path)

    # Basic validation
    missing = [c for c in READING_FIELDS + EQUIPMENT_FIELDS if c not in df.columns]
    if missing:
        raise ValueError(f"{in_path.name}: missing columns: {missing}")

    # Normalize boolean columns (handles "True"/"False" strings)
    for c in EQUIPMENT_FIELDS:
        if df[c].dtype == object:
            df[c] = df[c].astype(str).str.strip().str.lower().map({"true": True, "false": False})
        df[c] = df[c].fillna(False).astype(bool)

    # Build prev_* columns by shifting the equipment columns
    for c in EQUIPMENT_FIELDS:
        df[f"prev_{c}"] = df[c].shift(1, fill_value=False).astype(bool)

    if drop_first:
        df = df.iloc[1:].reset_index(drop=True)

    # Reorder columns nicely: readings, prev_*, commands
    ordered_cols = (
        READING_FIELDS
        + [f"prev_{c}" for c in EQUIPMENT_FIELDS]
        + EQUIPMENT_FIELDS
    )
    df = df[ordered_cols]

    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(out_path, index=False)


def main():
    parser = argparse.ArgumentParser(
        description="Add prev_* equipment state columns to greenhouse CSV datasets."
    )
    parser.add_argument(
        "--input_dir", required=True,
        help="Folder containing CSV files to convert"
    )
    parser.add_argument(
        "--output_dir", required=True,
        help="Folder where converted CSV files will be written"
    )
    parser.add_argument(
        "--drop_first", action="store_true",
        help="Drop the first row (since prev_* is artificial there)"
    )
    parser.add_argument(
        "--suffix", default="_with_prev",
        help="Suffix added to output filenames (before .csv)"
    )

    args = parser.parse_args()
    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    csv_files = sorted(in_dir.glob("*.csv"))
    if not csv_files:
        raise SystemExit(f"No .csv files found in {in_dir}")

    for in_path in csv_files:
        out_name = in_path.stem + args.suffix + in_path.suffix
        out_path = out_dir / out_name

        convert_file(in_path, out_path, drop_first=args.drop_first)
        print(f"Converted: {in_path.name} -> {out_path}")

    print("Done.")


if __name__ == "__main__":
    main()
