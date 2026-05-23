from pathlib import Path
import sqlite3
from typing import List, Optional

from fastapi import FastAPI, Query
from pydantic import BaseModel, Field

from app.intent_model import IntentRecognizer
from app.zsc_classifier import classify_text
from app.llm_summary import generate_stable_summary, is_ollama_available
from app.monitoring import compute_kpis

app = FastAPI(
    title="Pályázati felhívás kockázati API",
    description="PDF alapú pályázati felhívás elemző API: strukturált mezőkinyerés, ZSC kategorizálás, intent felismerés, Mistral/Ollama LLM összefoglaló és monitoring KPI-k.",
    version="1.1"
)

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "grants.db"
_intent_model = None


def get_intent_model():
    global _intent_model
    if _intent_model is None:
        _intent_model = IntentRecognizer()
    return _intent_model


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str
    database_exists: bool
    ollama_available: bool
    ollama_info: str


class TextRequest(BaseModel):
    text: str = Field(..., description="Elemzendő magyar nyelvű szöveg")


class ClassifyResponse(BaseModel):
    category: str


class IntentResponse(BaseModel):
    intent: str
    probabilities: dict = Field(default_factory=dict)


class SummarizeResponse(BaseModel):
    summary: str


class GrantResponse(BaseModel):
    fajlnev: Optional[str] = None
    felhivas_kod: Optional[str] = None
    cim: Optional[str] = None
    kedvezmenyezett: Optional[str] = None
    tevekenysegi_kor: Optional[str] = None
    konzorcium: Optional[str] = None
    tevekenysegek_szama: Optional[int] = None
    kezdes: Optional[str] = None
    vege: Optional[str] = None
    min_tamogatas: Optional[int] = None
    max_tamogatas: Optional[int] = None
    keretosszeg: Optional[int] = None
    tamogatas_tipusa: Optional[str] = None
    tamogatasi_logika: Optional[str] = None
    onero_szukseges: Optional[str] = None
    onero_szazalek: Optional[int] = None
    eloleg_szazalek: Optional[int] = None
    max_eloleg: Optional[int] = None
    projekt_ido_honap: Optional[int] = None
    helyszin: Optional[str] = None
    projektek_szama: Optional[int] = None
    zsc_kategoria: Optional[str] = None
    intent: Optional[str] = None
    kockazati_pont: Optional[float] = None
    kockazati_kategoria: Optional[str] = None
    llm_osszefoglalo: Optional[str] = None


class SearchResultResponse(BaseModel):
    felhivas_kod: Optional[str] = None
    cim: Optional[str] = None
    keretosszeg: Optional[int] = None
    eloleg_szazalek: Optional[int] = None
    kockazati_kategoria: Optional[str] = None


class HighRiskResponse(BaseModel):
    felhivas_kod: Optional[str] = None
    cim: Optional[str] = None
    keretosszeg: Optional[int] = None
    eloleg_szazalek: Optional[int] = None
    projektek_szama: Optional[int] = None
    kockazati_pont: Optional[float] = None
    kockazati_kategoria: Optional[str] = None


def fetch_all_rows():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM grants")
    rows = cursor.fetchall()
    conn.close()
    return rows


def row_to_grant(r):
    return {
        "fajlnev": r["file_name"],
        "felhivas_kod": r["call_code"],
        "cim": r["title"],
        "kedvezmenyezett": r["beneficiary_text"],
        "tevekenysegi_kor": r["activity_text"] if "activity_text" in r.keys() else None,
        "konzorcium": r["consortium_allowed"],
        "tevekenysegek_szama": r["activity_count"],
        "kezdes": r["submission_start"],
        "vege": r["submission_end"],
        "min_tamogatas": r["min_support"],
        "max_tamogatas": r["max_support"],
        "keretosszeg": r["total_budget_huf"],
        "tamogatas_tipusa": r["support_type"],
        "tamogatasi_logika": r["support_logic_text"] if "support_logic_text" in r.keys() else None,
        "onero_szukseges": r["own_fund_required"],
        "onero_szazalek": r["own_fund_percent"],
        "eloleg_szazalek": r["advance_percent"],
        "max_eloleg": r["advance_max"],
        "projekt_ido_honap": r["project_duration_months"],
        "helyszin": r["location_text"],
        "projektek_szama": r["project_count"],
        "zsc_kategoria": r["zsc_category"],
        "intent": r["intent"],
        "kockazati_pont": r["risk_score"],
        "kockazati_kategoria": r["risk_category"],
        "llm_osszefoglalo": r["llm_summary"],
    }


@app.get("/", response_model=RootResponse, summary="API állapot")
def root():
    return {"message": "Pályázati felhívás kockázati API működik"}


@app.get("/health", response_model=HealthResponse, summary="Health check")
def health():
    ok, info = is_ollama_available()
    return {"status": "ok", "database_exists": DB_PATH.exists(), "ollama_available": ok, "ollama_info": info}


@app.get("/grants", response_model=List[GrantResponse], summary="Felhívások lekérdezése")
def get_grants():
    if not DB_PATH.exists():
        return []
    return [row_to_grant(r) for r in fetch_all_rows()]


@app.get("/grants/{call_code}", response_model=Optional[GrantResponse], summary="Egy felhívás lekérdezése")
def get_grant(call_code: str):
    if not DB_PATH.exists():
        return None
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute("SELECT * FROM grants WHERE call_code = ? LIMIT 1", (call_code,))
    row = cur.fetchone()
    conn.close()
    return row_to_grant(row) if row else None


@app.get("/search", response_model=List[SearchResultResponse], summary="Keresés felhívások között")
def search_grants(
    advance_percent: Optional[int] = Query(default=None),
    risk_category: Optional[str] = Query(default=None),
    support_type: Optional[str] = Query(default=None),
    consortium_allowed: Optional[str] = Query(default=None),
):
    if not DB_PATH.exists():
        return []
    result = []
    for r in fetch_all_rows():
        if advance_percent is not None and r["advance_percent"] != advance_percent:
            continue
        if risk_category is not None and r["risk_category"] != risk_category:
            continue
        if support_type is not None and r["support_type"] != support_type:
            continue
        if consortium_allowed is not None and r["consortium_allowed"] != consortium_allowed:
            continue
        result.append({
            "felhivas_kod": r["call_code"],
            "cim": r["title"],
            "keretosszeg": r["total_budget_huf"],
            "eloleg_szazalek": r["advance_percent"],
            "kockazati_kategoria": r["risk_category"],
        })
    return result


@app.get("/high-risk", response_model=List[HighRiskResponse], summary="Magas kockázatú felhívások")
def high_risk():
    if not DB_PATH.exists():
        return []
    return [
        {
            "felhivas_kod": r["call_code"],
            "cim": r["title"],
            "keretosszeg": r["total_budget_huf"],
            "eloleg_szazalek": r["advance_percent"],
            "projektek_szama": r["project_count"],
            "kockazati_pont": r["risk_score"],
            "kockazati_kategoria": r["risk_category"],
        }
        for r in fetch_all_rows() if r["risk_category"] in ["magas", "kiemelt"]
    ]


@app.post("/classify", response_model=ClassifyResponse, summary="ZSC/HF jellegű tematikus kategorizálás")
def classify(req: TextRequest):
    return {"category": classify_text(req.text)}


@app.post("/intent", response_model=IntentResponse, summary="Szándékfelismerés")
def intent(req: TextRequest):
    model = get_intent_model()
    return {"intent": model.predict(req.text), "probabilities": model.predict_proba(req.text)}


@app.post("/summarize", response_model=SummarizeResponse, summary="Mistral/Ollama magyar LLM összefoglaló")
def summarize(req: TextRequest):
    return {"summary": generate_stable_summary(req.text)}


@app.get("/monitoring/kpis", summary="Monitoring KPI-k")
def monitoring_kpis():
    return compute_kpis()
