"""
Ingest pipeline: PDF-ek feldolgozása és adatbázisba mentése.

Futtatás:
    python -m app.ingest
"""
from datetime import datetime, timezone
from pathlib import Path

from app.extractor import read_pdf_text, extract_fields
from app.risk_model import compute_risk
from app.zsc_classifier import classify_text
from app.intent_model import IntentRecognizer
from app.db import get_connection, create_table, insert_record, delete_existing_by_call_code, clear_table
from app.llm_summary import generate_llm_indicator_material
import re

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data" / "pdfs"
PDF_LIMIT = int(__import__("os").environ.get("PDF_LIMIT", "3"))
LLM_MODEL = __import__("os").environ.get("OLLAMA_MODEL", "mistral")

print("📁 DATA_DIR:", DATA_DIR)

# Intent recognizer egyszer töltődik be
_intent_recognizer = None


def get_intent_recognizer():
    global _intent_recognizer
    if _intent_recognizer is None:
        _intent_recognizer = IntentRecognizer()
    return _intent_recognizer



def call_code_from_filename(file_path: Path) -> str:
    """Egyedi, jól olvasható felhíváskód képzése a PDF fájl nevéből.

    Azért szükséges, mert több PDF szövegében a regex csak a közös "GINOP"
    programnevet találta meg. Ilyenkor az adatbázisban minden feldolgozott rekord
    ugyanazzal a kulccsal mentődött, ezért a Streamlit felületen végül csak egy
    felhívás látszott.
    """
    stem = file_path.stem.lower()
    stem = stem.replace("ginopplusz", "ginop-plusz")
    m = re.search(r"ginop[-_ ]?plusz[-_ ]?(\d+)[-_ ]?(\d+)[-_ ]?(\d+)?[-_ ]?(\d{2})", stem)
    if m:
        a, b, c, year = m.groups()
        if c:
            return f"GINOP_PLUSZ-{a}.{b}.{c}-{year}"
        return f"GINOP_PLUSZ-{a}.{b}-{year}"
    return file_path.stem

def generate_stable_summary(data: dict) -> str:
    """Determinisztikus, adatalapú kockázati összefoglaló."""
    title = data.get("title") or "nincs adat"
    call_code = data.get("call_code") or "nincs adat"
    risk = data.get("risk_category") or "ismeretlen"
    score = data.get("risk_score")
    support_type = data.get("support_type") or "nincs adat"
    advance = data.get("advance_percent")
    duration = data.get("project_duration_months")
    own_fund = data.get("own_fund_required") or "nincs adat"
    consortium = data.get("consortium_allowed") or "nincs adat"
    max_support = data.get("max_support")
    advance_text = f"{advance}%" if advance is not None else "ismeretlen"
    duration_text = f"{duration} hónap" if duration is not None else "ismeretlen"
    support_text = f"{max_support/1e6:.0f} M Ft" if max_support else "ismeretlen"
    score_text = f" ({score} pont)" if score is not None else ""
    return (
        f"A(z) {call_code} azonosítójú ({title}) felhívás automatikus kockazati minősítése: "
        f"{risk.upper()}{score_text}. "
        f"Támogatás tipusa: {support_type} | Max összeg: {support_text} | "
        f"Előleg: {advance_text} | Futamidő: {duration_text}. "
        f"Önerő szükséges: {own_fund} | Konzorcium: {consortium}. "
        f"Az LLM indikátorelemzés eredménye a LLM demo kimenet szekcióban található."
    )

def process_file(conn, file_path: Path):
    try:
        print(f"\n📄 Feldolgozás: {file_path.name}")

        # 1. PDF szöveg kinyerése
        text = read_pdf_text(str(file_path))
        if not text or len(text.strip()) < 50:
            print("⚠️  Üres vagy túl rövid szöveg, kihagyás")
            return

        # 2. Strukturált mezők
        data = extract_fields(text)
        data["file_name"] = file_path.name

        # Egyedi felhíváskód biztosítása. Ha a PDF szövegéből csak a túl általános
        # programnév jön ki (pl. GINOP), akkor a fájlnévből képzünk azonosítót.
        extracted_code = str(data.get("call_code") or "").strip()
        if extracted_code.upper() in ["GINOP", "EFOP", "TOP", "DIMOP", "RRF", "VEKOP", ""]:
            data["call_code"] = call_code_from_filename(file_path)

        if not data.get("title"):
            data["title"] = file_path.stem

        # 3. Kockázati modell
        try:
            risk_score, risk_category, _ = compute_risk(data)
        except Exception as e:
            print(f"⚠️  Kockázati modell hiba: {e}")
            risk_score, risk_category = None, "nincs adat"
        data["risk_score"] = risk_score
        data["risk_category"] = risk_category

        # 4. ZSC kategorizálás
        try:
            data["zsc_category"] = classify_text(text[:1500])
        except Exception as e:
            print(f"⚠️  ZSC hiba: {e}")
            data["zsc_category"] = "ismeretlen"

        # 5. Intent felismerés
        try:
            recognizer = get_intent_recognizer()
            data["intent"] = recognizer.predict(text[:2000])
        except Exception as e:
            print(f"⚠️  Intent hiba: {e}")
            data["intent"] = "unknown"

        # 6. LLM összefoglaló (Ollama/Mistral, magyar nyelvű prompt)
        print("🤖 LLM összefoglaló generálása...")
        try:
            data["llm_demo"] = generate_llm_indicator_material(text, model=LLM_MODEL)
        except Exception as e:
            print(f"⚠️  LLM hiba: {e}")
            data["llm_demo"] = "LLM nem elérhető"

        # 7. Stabil, determinisztikus szöveg
        data["llm_summary"] = generate_stable_summary(data)

        # 8. Időbélyeg
        data["processed_at"] = datetime.now(timezone.utc).isoformat()

        # 9. DB mentés
        delete_existing_by_call_code(conn, data["call_code"])
        insert_record(conn, data)

        print("✅ Kész")

    except Exception as e:
        print(f"❌ Hiba feldolgozás közben: {e}")


def run():
    if not DATA_DIR.exists():
        print(f"❌ A data/pdfs mappa nem található: {DATA_DIR}")
        return

    pdf_files = sorted(DATA_DIR.glob("*.pdf"))[:PDF_LIMIT]

    if not pdf_files:
        print("⚠️  Nincs PDF a data/pdfs mappában.")
        return

    print(f"📁 {len(pdf_files)} fájl feldolgozása (első körben csak {PDF_LIMIT} PDF)...")

    conn = get_connection()
    create_table(conn)
    # Demo futásnál tiszta adatbázissal indulunk, hogy pontosan a kiválasztott
    # első 3 felhívás jelenjen meg a felületen, ne régi rekordok keveredjenek bele.
    clear_table(conn)

    for file_path in pdf_files:
        process_file(conn, file_path)

    conn.close()
    print("\n🎉 Feldolgozás kész")


if __name__ == "__main__":
    run()
