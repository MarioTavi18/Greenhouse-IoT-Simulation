from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import joblib
import pandas as pd

from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import (
    accuracy_score,
    balanced_accuracy_score,
    precision_recall_fscore_support,
    confusion_matrix,
)

# ---- Adjust if your folder name differs ----
DATA_ROOT = Path("C:\\Users\\Mario\\source\\repos\\GreenHouse_Project\\greenhouse_project\\datasets_split")

TRAIN_DIR = DATA_ROOT / "train"
VAL_DIR = DATA_ROOT / "val"
TEST_DIR = DATA_ROOT / "test"

MODEL_DIR = Path("trained_models")
MODEL_DIR.mkdir(parents=True, exist_ok=True)

EQUIPMENT = [
    "heater", "ventilation", "irrigation",
    "co2_injector", "lights", "dehumidifier", "light_blinds"
]

FEATURES = [
    "temperature", "humidity", "soil_moisture", "light_intensity", "co2_concentration",
    "prev_heater", "prev_ventilation", "prev_irrigation",
    "prev_co2_injector", "prev_lights", "prev_dehumidifier", "prev_light_blinds",
]


@dataclass
class SplitData:
    X: pd.DataFrame
    y: pd.Series


def load_split(split_dir: Path, target: str) -> SplitData:
    files = sorted(split_dir.glob("*.csv"))
    if not files:
        raise FileNotFoundError(f"No CSVs found in {split_dir.resolve()}")

    df = pd.concat([pd.read_csv(p) for p in files], ignore_index=True)

    missing = [c for c in FEATURES + [target] if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns in {split_dir}: {missing}")

    X = df[FEATURES].copy()

    # Ensure booleans become 0/1
    y = df[target]
    if y.dtype == object:
        y = y.astype(str).str.lower().map({"true": 1, "false": 0})
    y = y.fillna(0).astype(int)

    # Also convert prev_* to int if needed
    for c in FEATURES:
        if c.startswith("prev_") and X[c].dtype == object:
            X[c] = X[c].astype(str).str.lower().map({"true": 1, "false": 0}).fillna(0).astype(int)

    return SplitData(X=X, y=y)


def make_model() -> RandomForestClassifier:
    # Strong baseline, not too huge
    return RandomForestClassifier(
        n_estimators=400,
        max_depth=None,
        min_samples_leaf=2,
        class_weight="balanced_subsample",
        random_state=42,
        n_jobs=-1,
    )


def summarize(y_true, y_pred) -> dict:
    acc = accuracy_score(y_true, y_pred)
    bacc = balanced_accuracy_score(y_true, y_pred)
    prec, rec, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    cm = confusion_matrix(y_true, y_pred, labels=[0, 1])
    tn, fp, fn, tp = cm.ravel()

    prevalence = float(pd.Series(y_true).mean())  # fraction of 1s in true labels

    return {
        "accuracy": acc,
        "balanced_accuracy": bacc,
        "precision": prec,
        "recall": rec,
        "f1": f1,
        "prevalence_true": prevalence,
        "tn": int(tn), "fp": int(fp), "fn": int(fn), "tp": int(tp),
    }


def fmt_metrics(m: dict) -> str:
    return (
        f"acc={m['accuracy']:.4f}  bacc={m['balanced_accuracy']:.4f}  "
        f"prec={m['precision']:.4f}  rec={m['recall']:.4f}  f1={m['f1']:.4f}  "
        f"prevalence={m['prevalence_true']:.3f}  "
        f"(tn={m['tn']} fp={m['fp']} fn={m['fn']} tp={m['tp']})"
    )


def train_and_eval_one(target: str):
    train = load_split(TRAIN_DIR, target)
    val = load_split(VAL_DIR, target)
    test = load_split(TEST_DIR, target)

    model = make_model()
    model.fit(train.X, train.y)

    val_pred = model.predict(val.X)
    test_pred = model.predict(test.X)

    val_m = summarize(val.y, val_pred)
    test_m = summarize(test.y, test_pred)

    print(f"\n=== {target} ===")
    print("VAL : " + fmt_metrics(val_m))
    print("TEST: " + fmt_metrics(test_m))

    out_path = MODEL_DIR / f"rf_{target}.joblib"
    joblib.dump(model, out_path)
    print(f"Saved model -> {out_path}")


def main():
    print("Using:")
    print(f"  TRAIN={TRAIN_DIR.resolve()}")
    print(f"  VAL  ={VAL_DIR.resolve()}")
    print(f"  TEST ={TEST_DIR.resolve()}")
    print(f"  MODELS={MODEL_DIR.resolve()}")

    for target in EQUIPMENT:
        train_and_eval_one(target)


if __name__ == "__main__":
    main()
