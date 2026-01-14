import argparse
from pathlib import Path

import pandas as pd

def split_one_df(df: pd.DataFrame, seed: int, train: float, val: float):
    # Shuffle rows deterministically
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)

    n = len(df)
    n_train = int(n * train)
    n_val = int(n * val)
    n_test = n - n_train - n_val

    train_df = df.iloc[:n_train].copy()
    val_df = df.iloc[n_train:n_train + n_val].copy()
    test_df = df.iloc[n_train + n_val:].copy()

    assert len(test_df) == n_test
    return train_df, val_df, test_df


def main():
    parser = argparse.ArgumentParser(
        description="Balanced split: split each CSV into train/val/test, preserving equal config contribution."
    )
    parser.add_argument("--input_dir", required=True, help="Folder with per-config CSV files (with prev_ columns).")
    parser.add_argument("--output_dir", required=True, help="Output folder. Will create train/ val/ test/ subfolders.")
    parser.add_argument("--seed", type=int, default=42, help="Shuffle seed (reproducible).")
    parser.add_argument("--train", type=float, default=0.70, help="Train ratio.")
    parser.add_argument("--val", type=float, default=0.15, help="Validation ratio.")
    parser.add_argument("--test", type=float, default=0.15, help="Test ratio.")
    parser.add_argument("--pattern", type=str, default="*.csv", help="Glob pattern for input CSVs.")
    args = parser.parse_args()

    if abs((args.train + args.val + args.test) - 1.0) > 1e-9:
        raise SystemExit("train + val + test must sum to 1.0")

    in_dir = Path(args.input_dir)
    out_dir = Path(args.output_dir)

    train_dir = out_dir / "train"
    val_dir = out_dir / "val"
    test_dir = out_dir / "test"
    train_dir.mkdir(parents=True, exist_ok=True)
    val_dir.mkdir(parents=True, exist_ok=True)
    test_dir.mkdir(parents=True, exist_ok=True)

    files = sorted(in_dir.glob(args.pattern))
    if not files:
        raise SystemExit(f"No files found in {in_dir} matching {args.pattern}")

    total_counts = {"train": 0, "val": 0, "test": 0}

    for f in files:
        df = pd.read_csv(f)

        # Optional: make per-file seed stable but different across files
        file_seed = (hash(f.name) ^ args.seed) & 0xFFFFFFFF

        tr, va, te = split_one_df(df, seed=file_seed, train=args.train, val=args.val)

        tr_path = train_dir / f.name
        va_path = val_dir / f.name
        te_path = test_dir / f.name

        tr.to_csv(tr_path, index=False)
        va.to_csv(va_path, index=False)
        te.to_csv(te_path, index=False)

        total_counts["train"] += len(tr)
        total_counts["val"] += len(va)
        total_counts["test"] += len(te)

        print(f"{f.name}: train={len(tr)} val={len(va)} test={len(te)}")

    print("\nTOTALS")
    print(f"train={total_counts['train']} val={total_counts['val']} test={total_counts['test']}")


if __name__ == "__main__":
    main()
