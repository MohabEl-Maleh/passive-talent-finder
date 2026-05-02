# ml/scripts/train_on_kaggle_dataset.py
#
# Training script for the Kaggle Resume Dataset (snehaanbhawal/resume-dataset)
#
# Dataset columns:
#   ID          → unique identifier
#   Resume_str  → full resume text ← we use this
#   Resume_html → HTML version (ignored)
#   Category    → job category (HR, Engineering, Finance, etc.)
#
# What this script does:
#   1. Loads the CSV
#   2. Parses each resume using cv_parser
#   3. Computes passivity + fit scores for each
#   4. Trains a Random Forest classifier to predict passivity tier
#   5. Saves the trained model for use in the FastAPI backend
#
# Run from the ml/scripts/ directory:
#   python train_on_kaggle_dataset.py --csv path/to/Resume.csv

import sys
import os
import argparse
import pandas as pd
import numpy as np
import joblib
from sklearn.ensemble import RandomForestClassifier, GradientBoostingClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, accuracy_score
from sklearn.preprocessing import LabelEncoder

# Add backend to path so we can import services
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../backend"))

from services.recruitment.cv_parser import parse_kaggle_csv_row
from services.ai.passivity_scorer import compute_passivity_score
from services.ai.fit_scorer import batch_fit_scores


def load_and_parse(csv_path: str) -> pd.DataFrame:
    """Load the Kaggle CSV and parse every resume row."""
    print(f"Loading dataset from {csv_path}...")
    df_raw = pd.read_csv(csv_path)
    print(f"  {len(df_raw)} resumes loaded. Columns: {list(df_raw.columns)}")

    records = []
    for _, row in df_raw.iterrows():
        parsed = parse_kaggle_csv_row(row.to_dict())
        if parsed:
            records.append(parsed)

    df = pd.DataFrame(records)
    print(f"  {len(df)} resumes successfully parsed.")
    return df


def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create ML features from parsed fields.
    These features train the Random Forest passivity classifier.
    """
    df = df.copy()

    # Numeric features
    df["tenure_months"]    = df["tenure_months"].fillna(0).clip(0, 120)
    df["years_experience"] = df["years_experience"].fillna(0).clip(0, 40)
    df["job_changes"]      = df["job_changes"].fillna(0).clip(0, 10)
    df["is_employed"]      = df["is_employed"].fillna(0).astype(int)

    # Encode seniority as ordinal
    seniority_map = {"junior": 0, "mid": 1, "senior": 2}
    df["seniority_encoded"] = df["seniority_level"].map(seniority_map).fillna(1)

    # Encode category (from Kaggle) as label
    le = LabelEncoder()
    df["category_encoded"] = le.fit_transform(df["industry"].fillna("Unknown"))

    # Compute passivity score as the training label
    df["passivity_score"] = df.apply(
        lambda r: compute_passivity_score(
            tenure_months=r["tenure_months"],
            is_employed=r["is_employed"],
            job_changes=r["job_changes"],
            seniority_level=r["seniority_level"],
        ), axis=1
    )

    # Convert passivity score to 3-class label for classification
    # Low: 0–33, Medium: 34–66, High: 67–100
    df["passivity_tier"] = pd.cut(
        df["passivity_score"],
        bins=[-1, 33, 66, 101],
        labels=["low", "medium", "high"]
    )

    return df, le


def train_model(df: pd.DataFrame):
    """Train and evaluate a Random Forest classifier on passivity tier."""
    feature_cols = [
        "tenure_months",
        "years_experience",
        "job_changes",
        "is_employed",
        "seniority_encoded",
        "category_encoded",
    ]

    X = df[feature_cols]
    y = df["passivity_tier"]

    # Remove rows with NaN labels
    mask = y.notna()
    X, y = X[mask], y[mask]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print("\nTraining Random Forest classifier...")
    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=8,
        random_state=42,
        class_weight="balanced",
    )
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)
    acc = accuracy_score(y_test, y_pred)
    print(f"\nAccuracy: {acc:.3f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred))

    print("\nFeature Importances:")
    for feat, imp in sorted(zip(feature_cols, model.feature_importances_), key=lambda x: -x[1]):
        print(f"  {feat:25s}: {imp:.4f}")

    return model


def save_model(model, output_path: str):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    joblib.dump(model, output_path)
    print(f"\nModel saved to {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--csv", required=True, help="Path to Resume.csv from Kaggle dataset")
    parser.add_argument("--output", default="../../backend/models/passivity_model.pkl",
                        help="Where to save the trained model")
    args = parser.parse_args()

    df_parsed = load_and_parse(args.csv)
    df_features, label_encoder = engineer_features(df_parsed)
    model = train_model(df_features)
    save_model(model, args.output)

    print("\nDone. You can now run the FastAPI backend — it will load this model automatically.")
