"""
Intent felismerő modul – TF-IDF + Logistic Regression.

Besorolási osztályok:
  summary             – összefoglaló kérés
  indicator_analysis  – indikátor elemzés
  financial_info      – pénzügyi adatok
  eligibility         – kedvezményezetti kör
  risk_analysis       – kockázati elemzés
"""
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "models"


class IntentRecognizer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), max_features=5000)
        self.model = LogisticRegression(max_iter=1000, C=1.0)
        self._train()

    def _train(self):
        train_texts = [
            # summary
            "Foglald össze ezt a pályázati felhívást",
            "Készíts rövid összefoglalót a dokumentumról",
            "Mi a felhívás lényege",
            "Adj rövid summaryt",
            "Miről szól ez a pályázat",
            # indicator_analysis
            "Milyen indikátorok vannak a felhívásban",
            "Elemezd az indikátorokat",
            "Milyen eredményességi mutatók szerepelnek",
            "Indikátorértékelést kérek",
            "Mérési célértékek elemzése",
            # financial_info
            "Mekkora a támogatás összege",
            "Van önerő kötelezettség",
            "Mennyi az előleg mértéke",
            "Mutasd a pénzügyi feltételeket",
            "Keretösszeg és maximális támogatás",
            # eligibility
            "Kik pályázhatnak",
            "Ki lehet kedvezményezett",
            "Milyen szervezetek jogosultak",
            "Kedvezményezetti kör meghatározása",
            "Konzorciumi benyújtás lehetséges",
            # risk_analysis
            "Milyen kockázatok vannak",
            "Készíts kockázati elemzést",
            "Mi a fő ellenőrzési kockázat",
            "Kockázatértékelést kérek",
            "Kockázati pontszám magyarázata",
        ]

        train_labels = (
            ["summary"] * 5
            + ["indicator_analysis"] * 5
            + ["financial_info"] * 5
            + ["eligibility"] * 5
            + ["risk_analysis"] * 5
        )

        X = self.vectorizer.fit_transform(train_texts)
        self.model.fit(X, train_labels)

    def predict(self, text: str) -> str:
        if not text or not str(text).strip():
            return "unknown"
        X = self.vectorizer.transform([str(text)[:2000]])
        return self.model.predict(X)[0]

    def predict_proba(self, text: str) -> dict:
        """Visszaadja az összes osztály valószínűségét."""
        if not text or not str(text).strip():
            return {}
        X = self.vectorizer.transform([str(text)[:2000]])
        proba = self.model.predict_proba(X)[0]
        return dict(zip(self.model.classes_, proba))

    def save(self, path: Path = None):
        """Modell mentése joblib formátumban."""
        path = path or MODEL_DIR
        path.mkdir(parents=True, exist_ok=True)
        joblib.dump(self.vectorizer, path / "intent_vectorizer.joblib")
        joblib.dump(self.model, path / "intent_model.joblib")
        print(f"✅ Intent modell elmentve: {path}")

    @classmethod
    def load(cls, path: Path = None):
        """Elmentett modell betöltése."""
        path = path or MODEL_DIR
        obj = cls.__new__(cls)
        obj.vectorizer = joblib.load(path / "intent_vectorizer.joblib")
        obj.model = joblib.load(path / "intent_model.joblib")
        return obj
