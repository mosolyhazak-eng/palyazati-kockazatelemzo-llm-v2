"""
Monitoring és loggolás modul.

KPI-k:
  - feldolgozott PDF-ek száma
  - kockázati kategóriák megoszlása
  - ZSC kategóriák megoszlása
  - LLM sikerességi arány
  - intent megoszlás
  - data drift jelzők (mezők kitöltöttsége)

Naplózás: logs/pipeline.log (JSON sorok)
"""
import json
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "grants.db"
LOG_DIR = BASE_DIR / "logs"
LOG_FILE = LOG_DIR / "pipeline.log"

LOG_DIR.mkdir(exist_ok=True)

# JSON alapú file logger
json_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
json_handler.setLevel(logging.INFO)

logger = logging.getLogger("pipeline_monitor")
logger.setLevel(logging.INFO)
logger.addHandler(json_handler)
logger.addHandler(logging.StreamHandler())


def log_event(event_type: str, data: dict):
    """Strukturált JSON log bejegyzés írása."""
    entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "event": event_type,
        **data,
    }
    logger.info(json.dumps(entry, ensure_ascii=False))


def log_file_processed(file_name: str, call_code: str, risk_category: str,
                        zsc_category: str, intent: str, llm_ok: bool):
    log_event("file_processed", {
        "file_name": file_name,
        "call_code": call_code,
        "risk_category": risk_category,
        "zsc_category": zsc_category,
        "intent": intent,
        "llm_ok": llm_ok,
    })


def log_pipeline_run(total: int, success: int, failed: int, duration_sec: float):
    log_event("pipeline_run", {
        "total_files": total,
        "success": success,
        "failed": failed,
        "duration_sec": round(duration_sec, 2),
    })


def compute_kpis() -> dict:
    """
    KPI-k számítása az adatbázisból.
    
    Visszaadott metrikák:
      - total_grants          : összes rekord
      - risk_distribution     : kockázati megoszlás
      - zsc_distribution      : ZSC kategória megoszlás
      - intent_distribution   : intent megoszlás
      - llm_missing_rate      : LLM hiányosság aránya (data quality)
      - call_code_missing     : hiányzó felhívás kód
      - title_missing         : hiányzó cím
      - advance_missing       : hiányzó előleg adat
    """
    if not DB_PATH.exists():
        return {"error": "grants.db nem található"}

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    cur.execute("SELECT COUNT(*) as n FROM grants")
    total = cur.fetchone()["n"]

    if total == 0:
        conn.close()
        return {"total_grants": 0}

    # Kockázati megoszlás
    cur.execute("SELECT risk_category, COUNT(*) as n FROM grants GROUP BY risk_category")
    risk_dist = {r["risk_category"] or "ismeretlen": r["n"] for r in cur.fetchall()}

    # ZSC megoszlás
    cur.execute("SELECT zsc_category, COUNT(*) as n FROM grants GROUP BY zsc_category")
    zsc_dist = {r["zsc_category"] or "ismeretlen": r["n"] for r in cur.fetchall()}

    # Intent megoszlás
    cur.execute("SELECT intent, COUNT(*) as n FROM grants GROUP BY intent")
    intent_dist = {r["intent"] or "unknown": r["n"] for r in cur.fetchall()}

    # Data quality / drift detekció
    cur.execute("SELECT COUNT(*) as n FROM grants WHERE llm_summary IS NULL OR llm_summary = 'LLM nem elérhető'")
    llm_missing = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM grants WHERE call_code IS NULL OR call_code = ''")
    call_code_missing = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM grants WHERE title IS NULL OR title = ''")
    title_missing = cur.fetchone()["n"]

    cur.execute("SELECT COUNT(*) as n FROM grants WHERE advance_percent IS NULL")
    advance_missing = cur.fetchone()["n"]

    conn.close()

    return {
        "total_grants": total,
        "risk_distribution": risk_dist,
        "zsc_distribution": zsc_dist,
        "intent_distribution": intent_dist,
        "llm_missing_rate": round(llm_missing / total, 3),
        "call_code_missing": call_code_missing,
        "title_missing": title_missing,
        "advance_missing_rate": round(advance_missing / total, 3),
        "computed_at": datetime.utcnow().isoformat(),
    }


def print_kpi_report():
    kpis = compute_kpis()
    print("\n" + "=" * 50)
    print("📊 KPI RIPORT")
    print("=" * 50)
    for k, v in kpis.items():
        if isinstance(v, dict):
            print(f"\n{k}:")
            for sub_k, sub_v in v.items():
                print(f"  {sub_k}: {sub_v}")
        else:
            print(f"{k}: {v}")
    print("=" * 50)


if __name__ == "__main__":
    print_kpi_report()
