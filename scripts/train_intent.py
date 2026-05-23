"""Intent modell tanítása CSV alapján.

Futtatás:
    python scripts/train_intent.py
"""
from pathlib import Path
import pandas as pd
import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report

BASE_DIR = Path(__file__).resolve().parent.parent
TRAIN_PATH = BASE_DIR / "data" / "training" / "intent_examples.csv"
MODEL_DIR = BASE_DIR / "models"


def main():
    df = pd.read_csv(TRAIN_PATH)
    X_train, X_test, y_train, y_test = train_test_split(
        df["text"], df["label"], test_size=0.25, random_state=42, stratify=df["label"]
    )
    vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    model = LogisticRegression(max_iter=1000, C=1.0)
    model.fit(X_train_vec, y_train)
    pred = model.predict(X_test_vec)

    MODEL_DIR.mkdir(exist_ok=True)
    joblib.dump(vectorizer, MODEL_DIR / "intent_vectorizer.joblib")
    joblib.dump(model, MODEL_DIR / "intent_model.joblib")

    print("Intent modell elmentve:", MODEL_DIR)
    print(classification_report(y_test, pred, zero_division=0))


if __name__ == "__main__":
    main()
