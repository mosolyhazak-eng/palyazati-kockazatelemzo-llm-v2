"""Tematikus kategorizáló.

Alapértelmezésben offline, kulcsszavas kategorizálást használ, ezért nem tölt le
HuggingFace modellt és nem ír HF_TOKEN figyelmeztetést. Ha mégis HF zero-shot kell:
    USE_HF_ZSC=1 python -m app.ingest
"""
import os

LABELS = [
    "vállalkozásfejlesztés",
    "önkormányzati fejlesztés",
    "oktatás",
    "energia",
    "egészségügy",
    "kutatás-fejlesztés",
    "digitalizáció",
    "infrastruktúra",
]

KEYWORDS = {
    "vállalkozásfejlesztés": ["kkv", "vállalkozás", "mikro", "kis- és középvállalkoz", "termelési", "üzleti"],
    "önkormányzati fejlesztés": ["önkormányzat", "település", "helyi", "vármegye"],
    "oktatás": ["oktatás", "képzés", "szakképzés", "tanuló", "kompetencia"],
    "energia": ["energia", "energetika", "megújuló", "napelem", "hatékonyság"],
    "egészségügy": ["egészség", "egészségügyi", "beteg", "ellátás"],
    "kutatás-fejlesztés": ["kutatás", "fejlesztés", "innováció", "k+f", "kfi", "technológia"],
    "digitalizáció": ["digitális", "digitalizáció", "informatikai", "szoftver", "ikt"],
    "infrastruktúra": ["infrastruktúra", "építés", "eszközbeszerzés", "beruházás", "kapacitás"],
}

_classifier = None


def _classify_keyword(text: str) -> str:
    lower = (text or "").lower()
    scores = {label: sum(lower.count(k) for k in kws) for label, kws in KEYWORDS.items()}
    best_label, best_score = max(scores.items(), key=lambda x: x[1])
    return best_label if best_score > 0 else "ismeretlen"


def get_classifier():
    global _classifier
    if _classifier is None:
        from transformers import pipeline
        _classifier = pipeline("zero-shot-classification", model="facebook/bart-large-mnli")
    return _classifier


def classify_text(text: str) -> str:
    if not text or not str(text).strip():
        return "ismeretlen"
    if os.environ.get("USE_HF_ZSC", "0") != "1":
        return _classify_keyword(str(text)[:8000])
    try:
        classifier = get_classifier()
        result = classifier(str(text)[:1000], LABELS)
        return result["labels"][0]
    except Exception:
        return _classify_keyword(str(text)[:8000])
