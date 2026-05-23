from PyPDF2 import PdfReader


def parse_pdf(file_path):
    text = ""

    try:
        reader = PdfReader(str(file_path))

        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

    except Exception as e:
        print(f"❌ PDF olvasási hiba: {e}")
        return {}

    text = text.strip()

    # 🔧 egyszerű struktúra (demo-hoz elég)
    data = {
        "title": file_path.stem,
        "call_code": file_path.stem,
        "text": text,
        "beneficiary_text": "nincs adat",
        "consortium_allowed": "nincs adat",
        "activity_count": "nincs adat",
        "submission_start": "nincs adat",
        "submission_end": "nincs adat",
        "min_support": "nincs adat",
        "max_support": "nincs adat",
        "total_budget_huf": "nincs adat",
        "support_type": "nincs adat",
        "own_fund_required": "nincs adat",
        "advance_percent": "nincs adat",
        "project_duration_months": "nincs adat",
        "project_count": "nincs adat",
    }

    return data