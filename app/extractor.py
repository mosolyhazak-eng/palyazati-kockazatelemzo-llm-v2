import re
from pathlib import Path


def read_pdf_text(pdf_path: str) -> str:
    """PDF szövegének gyors kinyerése.

    Elsőként PyMuPDF-et próbál, mert sokkal gyorsabb WSL/Ubuntu alatt.
    Ha nincs telepítve, PyPDF2-re, végül pdfplumberre vált.
    """
    path = str(pdf_path)

    # 1) PyMuPDF / fitz – gyors
    try:
        import fitz  # pymupdf
        parts = []
        with fitz.open(path) as doc:
            for page in doc:
                txt = page.get_text("text")
                if txt:
                    parts.append(txt)
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 2) PyPDF2 – általában elérhető
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(path)
        parts = []
        for page in reader.pages:
            txt = page.extract_text() or ""
            if txt:
                parts.append(txt)
        text = "\n".join(parts).strip()
        if text:
            return text
    except Exception:
        pass

    # 3) pdfplumber – lassabb, de sok PDF-nél jó tartalék
    try:
        import pdfplumber
        parts = []
        with pdfplumber.open(path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    parts.append(page_text)
        return "\n".join(parts).strip()
    except Exception as e:
        raise RuntimeError(f"PDF szövegkinyerési hiba: {Path(pdf_path).name}: {e}")


def _to_int_huf(raw: str, unit: str | None = None):
    if not raw:
        return None
    s = raw.replace(" ", "").replace(".", "").replace(",", ".")
    try:
        val = float(s)
    except Exception:
        return None
    unit = (unit or "").lower()
    if "mrd" in unit or "milliárd" in unit:
        val *= 1_000_000_000
    elif "millió" in unit or "mft" in unit:
        val *= 1_000_000
    return int(val)




def _extract_section(text: str, headings: list[str], max_chars: int = 1200) -> str | None:
    """Egyszerű fejezetrészlet-kinyerés kereséshez és UI megjelenítéshez."""
    if not text:
        return None
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    joined = "\n".join(lines)
    lower = joined.lower()
    starts = []
    for h in headings:
        i = lower.find(h.lower())
        if i >= 0:
            starts.append(i)
    if not starts:
        return None
    start = min(starts)
    # következő tipikus fejezetcímig, de legfeljebb max_chars
    next_candidates = []
    for marker in ["jogosultsági", "támogatható", "nem támogatható", "pénzügyi", "elszámolható", "indikátor", "mérföldkő", "benyújtás", "kiválasztási", "kötelező", "projekt végrehajtása"]:
        j = lower.find(marker, start + 80)
        if j > start:
            next_candidates.append(j)
    end = min(next_candidates) if next_candidates else start + max_chars
    end = min(end, start + max_chars)
    snippet = joined[start:end].strip()
    return snippet[:max_chars] if snippet else None



def _clean_snippet(snippet: str, max_chars: int = 2500) -> str | None:
    if not snippet:
        return None
    snippet = re.sub(r"[ \t]+", " ", snippet)
    snippet = re.sub(r"\n{3,}", "\n\n", snippet)
    snippet = re.sub(r"\s*\|\s*", " | ", snippet)
    snippet = snippet.strip(" \n\t|.;")
    return snippet[:max_chars] if snippet else None



def _extract_activity_text(text: str, max_chars: int = 2200) -> str | None:
    """Támogatható tevékenységek célzott kinyerése.

    A rövid Q&A-szerű PDF-kivonatokban a korábbi általános szakaszkeresés
    gyakran továbbfutott a támogatási összeg, önerő vagy futamidő kérdésekig.
    Ez a függvény kizárólag a tevékenységi felsorolást tartja meg.
    """
    if not text:
        return None
    t = re.sub(r"\r", "\n", text)
    lower = t.lower()

    # Elsőként a PDF eleji „Rövid összefoglaló” táblázatból olvasunk.
    # Ez adja a leginkább UI-kompatibilis választ, pl. „Mikro-, kis-, és középvállalkozások”.
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    for i, ln in enumerate(lines[:180]):
        if re.search(r"ki\s+nyújthat\s+be\s+támogatási\s+kérelmet\??", ln, flags=re.I):
            collected = []
            for nxt in lines[i + 1:i + 45]:
                if re.search(r"nyújthat\s+be\s+támogatási\s+kérelmet\s+konzorcium|milyen\s+tevékenységek|mikor\s+lehet\s+benyújtani|a\s+támogatás\s+visszatérítendő", nxt, flags=re.I):
                    break
                if re.search(r"részletes\s+információk|felhívás\s+1\.1|1\.2\s+fejezetében|fejezetében\)?$", nxt, flags=re.I):
                    continue
                if re.fullmatch(r"\d+", nxt):
                    continue
                collected.append(nxt)
            summary = _clean_beneficiary_answer(" ".join(collected), max_chars=1200)
            if summary:
                return summary

    start_patterns = [
        r"milyen\s+tevékenységek\s+támogathatóak\??",
        r"2\.1\.?\s*milyen\s+tevékenységek\s+támogathatóak",
        r"támogatható\s+tevékenységek\s*/\s*tevékenységi\s+kör",
        r"önállóan\s+támogatható\s+tevékenységek",
    ]
    starts = []
    for pat in start_patterns:
        for m in re.finditer(pat, lower, flags=re.I):
            if m.start() > 1000:
                starts.append(m.start())
    if not starts:
        return None
    start = min(starts)

    end_patterns = [
        r"mikor\s+lehet\s+benyújtani",
        r"mennyi\s+támogatást\s+lehet\s+igényelni",
        r"kell-e\s+önerő",
        r"mennyi\s+előleg\s+igényelhető",
        r"mennyi\s+ideig\s+tart",
        r"\n\s*2\.2\.",
        r"\n\s*2\.3\.",
        r"\n\s*3\.",
    ]
    area = lower[start + 40:start + 7000]
    ends = []
    for pat in end_patterns:
        m = re.search(pat, area, flags=re.I)
        if m:
            ends.append(start + 40 + m.start())
    end = min(ends) if ends else start + max_chars
    snippet = t[start:min(end, start + max_chars)]
    snippet = re.sub(r"\(Részletes információk[^)]*\)", "", snippet, flags=re.I)
    snippet = re.sub(r"Milyen\s+tevékenységek\s+támogathatóak\??", "", snippet, flags=re.I)
    snippet = re.sub(r"\s+", " ", snippet).strip(" -–:;.")
    return _clean_snippet(snippet, max_chars=max_chars)


def _extract_location_text(text: str, max_chars: int = 1600) -> str | None:
    """Megvalósítási helyszín célzott kinyerése, tartalmi levágás nélkül."""
    if not text:
        return None
    t = re.sub(r"\r", "\n", text)
    lower = t.lower()
    start_patterns = [
        r"megvalósítás\s+helyszíne",
        r"a\s+fejlesztés\s+megvalósításának\s+helyszíne",
        r"területi\s+korlátozás",
        r"a\s+projekt\s+megvalósítási\s+területe",
    ]
    starts = []
    for pat in start_patterns:
        for m in re.finditer(pat, lower, flags=re.I):
            if m.start() > 1000:
                starts.append(m.start())
    if not starts:
        return None
    start = min(starts)
    end_patterns = [
        r"mikor\s+kezdhető\s+meg", r"mikor\s+lehet\s+benyújtani",
        r"a\s+projekt\s+végrehajtás", r"\n\s*1\.4\.", r"\n\s*1\.5\.",
        r"\n\s*2\.", r"\n\s*3\.",
    ]
    area = lower[start + 60:start + 5000]
    ends = []
    for pat in end_patterns:
        m = re.search(pat, area, flags=re.I)
        if m:
            ends.append(start + 60 + m.start())
    end = min(ends) if ends else start + max_chars
    snippet = t[start:min(end, start + max_chars)]
    snippet = re.sub(r"^területi\s+korlátozása\s*", "", snippet, flags=re.I)
    snippet = re.sub(r"\s+", " ", snippet).strip(" -–:;.")
    return _clean_snippet(snippet, max_chars=max_chars)



def _extract_advance_fields(text: str) -> tuple[int | None, int | None]:
    """Előleg kinyerése a konkrét „Mennyi előleg igényelhető?” válaszból.

    Korábban az általános „előleg ... %” keresés több felhívásnál a támogatási
    intenzitást vagy más százalékos értéket találta meg. Ezért először célzottan
    a kérdés-válasz részletben keresünk, és csak végső esetben használunk
    óvatos fallback mintát.
    """
    if not text:
        return None, None
    t = re.sub(r"\r", "\n", text)
    lower = t.lower()

    starts = [m.start() for m in re.finditer(r"mennyi\s+előleg\s+igényelhető\??", lower, flags=re.I)]

    # A kérdés a vezetői összefoglalóban, a tartalomjegyzékben és a részletes
    # 7.1 fejezetben is előfordulhat. Azt a részletet választjuk, amelyben
    # tényleges százalékos válasz van, és nem tartalomjegyzék-jellegű.
    zones = []
    for start in starts:
        z = t[start:start + 1400]
        if re.search(r"\d{1,3}\s*%", z) and "................" not in z:
            zones.append(z)
    if zones:
        # A rövid összefoglalóban szereplő válasz általában tisztább, ezért az első jó zónát használjuk.
        zone = zones[0]
    else:
        zone = ""
        m = re.search(r"előleg", lower, flags=re.I)
        if m:
            zone = t[m.start():m.start() + 800]

    if not zone:
        return None, None

    # Tipikus válasz: „100%, maximum 629 300 000 Ft” vagy „100%-a, de legfeljebb ...”
    pct = None
    pct_match = re.search(r"(\d{1,3})\s*%", zone)
    if pct_match:
        try:
            val = int(pct_match.group(1))
            if 0 <= val <= 100:
                pct = val
        except Exception:
            pct = None

    max_val = None
    max_match = re.search(r"(?:maximum|max\.?|legfeljebb)(?!\s*\d{1,3}\s*%)\s*([0-9][0-9\s\.,]*)\s*(Ft|forint|M\s*Ft|millió|mrd|milliárd)", zone, flags=re.I)
    if max_match:
        max_val = _to_int_huf(max_match.group(1), max_match.group(2) or "Ft")

    return pct, max_val


def _extract_support_logic_text(text: str, max_chars: int = 700) -> str | None:
    """A támogatás visszatérítendő/vissza nem térítendő logikájának kinyerése."""
    if not text:
        return None
    t = re.sub(r"\r", "\n", text)
    lower = t.lower()
    starts = [m.start() for m in re.finditer(r"a\s+támogatás\s+visszatérítendő\s+vagy\s+vissza\s+nem\s+térítendő\??", lower, flags=re.I)]
    starts_content = [x for x in starts if x > 5000]
    start = starts_content[0] if starts_content else (starts[0] if starts else None)
    if start is None:
        # Fallback: keressük a jellegzetes mondatot.
        m = re.search(r"visszatérítendő\s+támogatás[^\n\.]{0,300}vissza\s+nem\s+térítendővé\s+válik", lower, flags=re.I)
        if not m:
            return None
        start = max(0, m.start() - 60)

    zone = t[start:start + max_chars]
    # A következő Q&A blokk előtt levágjuk, hogy ne keveredjen bele az önerő, előleg vagy időtartam.
    stop = re.search(r"Kell-e\s+önerő|Mennyi\s+előleg|Mennyi\s+a\s+projekt", zone, flags=re.I)
    if stop:
        zone = zone[:stop.start()]
    # A kérdés/fejezethivatkozás levágása.
    zone = re.sub(r"A\s+támogatás\s+visszatérítendő\s+vagy\s+vissza\s+nem\s+térítendő\??", "", zone, flags=re.I)
    zone = re.sub(r"\(Részletes\s+információk[^)]*\)", "", zone, flags=re.I)
    zone = re.sub(r"\s+", " ", zone).strip(" -–:;.")
    return _clean_snippet(zone, max_chars=max_chars)


def _extract_own_fund_percent(text: str) -> int | None:
    """Önerő mértékének kinyerése, pl. „minimum 30% mértékben”."""
    lower = (text or "").lower()
    patterns = [
        r"kell-e\s+önerő[^%]{0,400}?(?:igen[^%]{0,200}?)?(?:minimum|legalább|minimális)\s+(\d{1,3})\s*%",
        r"önerő[^%]{0,250}?(?:minimum|legalább|minimális)\s+(\d{1,3})\s*%",
        r"(?:minimum|legalább|minimális)\s+(\d{1,3})\s*%[^.\n]{0,120}?önerő",
        r"saját\s+forrás[^%]{0,250}?(?:minimum|legalább|minimális)?\s*(\d{1,3})\s*%",
    ]
    for pat in patterns:
        m = re.search(pat, lower, flags=re.I | re.S)
        if m:
            try:
                val = int(m.group(1))
                if 0 <= val <= 100:
                    return val
            except Exception:
                pass
    return None

def _extract_beneficiary_text(text: str, max_chars: int = 2800) -> str | None:
    """A kedvezményezetti/támogatást igénylői kör célzott kinyerése.

    A GINOP Plusz felhívásokban a releváns rész többnyire az
    „1.1. Ki nyújthat be támogatási kérelmet?” fejezetben van. A korábbi
    általános keresés sokszor a tartalomjegyzéket vagy egy általános
    figyelmeztető mondatot fogott meg, ezért a kereső nem volt használható.
    """
    if not text:
        return None
    t = re.sub(r"\r", "\n", text)
    lower = t.lower()

    # Elsőként a PDF eleji „Rövid összefoglaló” táblázatból olvasunk.
    # Ez adja a leginkább UI-kompatibilis választ, pl. „Mikro-, kis-, és középvállalkozások”.
    lines = [ln.strip() for ln in t.splitlines() if ln.strip()]
    for i, ln in enumerate(lines[:180]):
        if re.search(r"ki\s+nyújthat\s+be\s+támogatási\s+kérelmet\??", ln, flags=re.I):
            collected = []
            for nxt in lines[i + 1:i + 45]:
                if re.search(r"nyújthat\s+be\s+támogatási\s+kérelmet\s+konzorcium|milyen\s+tevékenységek|mikor\s+lehet\s+benyújtani|a\s+támogatás\s+visszatérítendő", nxt, flags=re.I):
                    break
                if re.search(r"részletes\s+információk|felhívás\s+1\.1|1\.2\s+fejezetében|fejezetében\)?$", nxt, flags=re.I):
                    continue
                if re.fullmatch(r"\d+", nxt):
                    continue
                collected.append(nxt)
            summary = _clean_beneficiary_answer(" ".join(collected), max_chars=1200)
            if summary:
                return summary

    start_patterns = [
        r"1\.1\.\s*ki\s+nyújthat\s+be\s+támogatási\s+kérelmet\??",
        r"a\s+felhívásra\s+támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:",
        r"támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:",
        r"támogatást\s+igénylők\s+köre",
        r"kedvezményezettek\s+köre",
    ]
    # Elsőként a tényleges tartalmi mondatot keressük, mert a fejezetcím
    # a tartalomjegyzékben is előfordulhat.
    priority = []
    for pat in [r"a\s+felhívásra\s+támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:",
                r"támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:"]:
        for m in re.finditer(pat, lower, flags=re.I):
            if m.start() > 5000:
                priority.append(m.start())
    if priority:
        start = min(priority)
    else:
        starts = []
        for pat in start_patterns:
            for m in re.finditer(pat, lower, flags=re.I):
                if m.start() > 8000:  # tartalomjegyzék elkerülése
                    starts.append(m.start())
        if not starts:
            return None
        start = min(starts)

    end_patterns = [
        r"\n\s*1\.2\.", r"\n\s*1\.3\.", r"mikor\s+nem\s+nyújtható\s+be",
        r"mikor\s+lehet\s+benyújtani", r"a\s+támogatási\s+kérelem\s+benyújtás",
        r"\n\s*2\.", r"\n\s*3\.",
    ]
    end_candidates = []
    search_area = lower[start + 200:start + 9000]
    for pat in end_patterns:
        m = re.search(pat, search_area, flags=re.I)
        if m:
            end_candidates.append(start + 200 + m.start())
    end = min(end_candidates) if end_candidates else start + max_chars
    snippet = t[start:min(end, start + max_chars)]
    # Túl hosszú felsorolásnál a lényeg megtartása.
    snippet = re.sub(r"\n\s*\d+\s*\n", "\n", snippet)
    return _clean_snippet(snippet, max_chars=max_chars)


def _norm_indicator_code(match: re.Match) -> str:
    prefix = match.group(1).upper().replace(" ", "")
    num = match.group(2)
    # RCO 01 -> RCO01, RCR 19 -> RCR19
    if len(num) == 1:
        num = "0" + num
    return f"{prefix}{num}"


def _extract_indicator_text(text: str, max_items: int = 12) -> str | None:
    """Nevesített RCO/RCR/egyéb indikátorok kinyerése kóddal és névvel.

    Cél: az UI ne célmondatokat írjon indikátorként, hanem például RCR19, RCR25,
    RCO01 jellegű nevesített indikátorokat.
    """
    if not text:
        return None
    # Elsősorban a tényleges indikátortáblát keressük, nem a tartalomjegyzéket.
    lower = text.lower()
    code_pos = []
    for m0 in re.finditer(r"\b(?:rco|rcr|psr|op)\s*0?\d{1,3}\b", lower, flags=re.I):
        if m0.start() > 10000:
            code_pos.append(m0.start())
    if code_pos:
        start = max(0, min(code_pos) - 300)
    else:
        name_pos = [m.start() for m in re.finditer("indikátor neve", lower, flags=re.I) if m.start() > 10000]
        start = min(name_pos) if name_pos else 0
    zone = text[start:start + 65000]

    code_re = re.compile(r"\b(RCO|RCR|PSR|OP)\s*0?(\d{1,3})\b", re.I)
    matches = list(code_re.finditer(zone))
    if not matches:
        return None

    ignore = {
        "erfa", "esza", "ka", "eur", "db", "fő", "fo", "huf", "ft",
        "közös", "kozos", "kimeneti", "eredmény", "eredmeny", "vállalkozás",
        "vallalkozas", "éves fte", "eves fte", "mértékegység", "mertekegyseg",
        "típusa", "tipusa", "azonosító", "azonosito", "alap", "célérték", "célérték tervezése",
    }

    items = []
    seen = set()
    for idx, m in enumerate(matches):
        code = _norm_indicator_code(m)
        if code in seen:
            continue
        seen.add(code)
        seg_end = matches[idx + 1].start() if idx + 1 < len(matches) else min(len(zone), m.end() + 900)
        seg = zone[m.end():seg_end]
        seg = re.sub(r"[|•·]", "\n", seg)
        seg = re.sub(r"\s+", " ", seg)
        # Szüneteltetés tipikus meta-szavaknál, ha a név már összegyűlt.
        words = re.findall(r"[A-Za-zÁÉÍÓÖŐÚÜŰáéíóöőúüű0-9%/\-–()]+", seg)
        name_words = []
        for w in words:
            wl = w.lower().strip(" .,:;()")
            if not wl:
                continue
            # A táblázatok elején gyakran két Igen/Nem oszlop van; ezeket az elején eldobjuk,
            # de a névben szereplő „nem” szót megtartjuk (pl. vissza nem térítendő).
            if wl in {"igen", "nem"} and not name_words:
                continue
            if wl in ignore or re.fullmatch(r"\d+", wl):
                if len(name_words) >= 3:
                    break
                continue
            # Ha új kód kezdődne, álljunk meg.
            if re.fullmatch(r"RCO|RCR|PSR|OP", w, flags=re.I):
                break
            name_words.append(w)
            if len(name_words) >= 30:
                break
        name = " ".join(name_words).strip(" -–,.;")
        if not name or len(name) < 6:
            # fallback: rövid környezeti kivágat
            fallback = re.sub(r"\s+", " ", seg).strip()[:180]
            name = fallback
        if name and "indikátor neve" not in name.lower() and "op-kimeneti" not in name.lower():
            items.append(f"- **{code}** – {name}")
        if len(items) >= max_items:
            break

    return "\n".join(items) if items else None




def _clean_title_candidate(line: str) -> str | None:
    """Címjelölt tisztítása a PDF elején szereplő feliratokból."""
    if not line:
        return None
    s = re.sub(r"\s+", " ", line).strip(" -–—:;.,")
    if not s or len(s) < 8:
        return None
    sl = s.lower()
    bad = [
        "felhívás", "rövid összefoglaló", "ki nyújthat", "tartalomjegyzék",
        "módosítás", "verzió", "hatályos", "oldal", "www.", "http"
    ]
    if any(b in sl for b in bad):
        return None
    if re.search(r"\b(GINOP|DIMOP|EFOP|TOP|KEHOP|IKOP|MAHOP|VOP|RRF|VEKOP)[ _+-]*Plusz?[-\s]*\d", s, flags=re.I):
        return None
    # Ne legyen pusztán kód vagy nagyon technikai sor.
    if re.fullmatch(r"[A-Z0-9_ .+\-/]+", s) and len(s.split()) <= 3:
        return None
    return s[:280]


def _extract_title(text: str, call_code: str | None = None) -> str | None:
    """Felhívás címének kinyerése.

    Elsődlegesen a felhíváskód felett közvetlenül szereplő címsort keresi,
    mert a PDF-ek borítóján gyakran ez a valódi cím (pl. Magyar Falu
    Vállalkozás-újraindítási Program), alatta pedig külön sorban áll a kód.
    """
    if not text:
        return None
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    if not lines:
        return None
    code_line_idx = None
    code_re = re.compile(r"\b(GINOP|DIMOP|EFOP|TOP|KEHOP|IKOP|MAHOP|VOP|RRF|VEKOP)[ _+-]*(?:Plusz)?[-\s]*\d", re.I)
    if call_code:
        compact_call = re.sub(r"\s+", " ", str(call_code)).lower()
        for i, line in enumerate(lines[:90]):
            if compact_call and compact_call in re.sub(r"\s+", " ", line).lower():
                code_line_idx = i
                break
    if code_line_idx is None:
        for i, line in enumerate(lines[:90]):
            if code_re.search(line):
                code_line_idx = i
                break
    if code_line_idx is not None:
        # A cím gyakran több sorba törik közvetlenül a felhíváskód felett.
        title_parts = []
        for j in range(max(0, code_line_idx - 5), code_line_idx):
            cand = _clean_title_candidate(lines[j])
            if cand:
                title_parts.append(cand)
        if title_parts:
            joined = " ".join(title_parts)
            joined = re.sub(r"\s+", " ", joined).strip()
            return joined[:280]
    # Fallback: az első értelmes, nem kód jellegű borítósor.
    for line in lines[:60]:
        cand = _clean_title_candidate(line)
        if cand:
            return cand
    return lines[0][:280] if lines else None


def _clean_beneficiary_answer(snippet: str | None, max_chars: int = 1000) -> str | None:
    """Kedvezményezetti válasz tisztítása: csak a tényleges jogosulti kör maradjon."""
    if not snippet:
        return None
    s = re.sub(r"\s+", " ", snippet).strip(" -–—:;.")
    s = re.sub(r"\(Részletes\s+információk[^)]*\)", "", s, flags=re.I)
    # Rövid összefoglaló táblázatok: kérdés + válasz.
    s = re.sub(r"^\s*Ki\s+nyújthat\s+be\s+támogatási\s+kérelmet\??\s*", "", s, flags=re.I)
    s = re.sub(r"^\s*1\.1\.\s*Ki\s+nyújthat\s+be\s+támogatási\s+kérelmet\??\s*", "", s, flags=re.I)
    s = re.sub(r"^\s*A\s+felhívásra\s+támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:?", "", s, flags=re.I)
    s = re.sub(r"^\s*Támogatási\s+kérelmet\s+nyújthatnak\s+be\s*:?", "", s, flags=re.I)
    # Következő Q&A blokk előtt vágjuk el.
    stops = [
        r"Nyújthat\s+be\s+támogatási\s+kérelmet\s+konzorcium",
        r"Mikor\s+nem\s+nyújtható\s+be",
        r"Mikor\s+lehet\s+benyújtani",
        r"A\s+támogatási\s+kérelem\s+benyújtására\s+konzorciumi",
        r"1\.2\.", r"1\.3\.", r"2\."
    ]
    for pat in stops:
        m = re.search(pat, s, flags=re.I)
        if m and m.start() > 5:
            s = s[:m.start()]
            break
    s = re.sub(r"\s+", " ", s).strip(" -–—:;.")
    # Ha még mindig hosszú, a táblázatos válasz első mondata/felsorolása a lényeg.
    if len(s) > max_chars:
        cut = re.search(r"(?:\.|;|\n)", s[:max_chars])
        s = s[:max_chars].rstrip() + "…"
    return s if s else None

def extract_fields(text: str) -> dict:
    data = {}
    clean_text = text or ""
    lower = clean_text.lower()

    # --- Felhívás kód ---
    match = re.search(r"(GINOP\s*Plusz|GINOP\+|GINOP|EFOP\s*Plusz|TOP\s*Plusz|DIMOP\s*Plusz|RRF|VEKOP)[\w\-\.\+/\s]*\d[\w\-\.\+/]*", clean_text, re.I)
    data["call_code"] = re.sub(r"\s+", " ", match.group(0)).strip(" .,;:") if match else None

    # --- Cím ---
    # A PDF-ek borítóján a valódi cím sokszor a felhíváskód felett szerepel.
    data["title"] = _extract_title(clean_text, data.get("call_code"))

    # --- Előleg % és maximum ---
    # Célzottan a „Mennyi előleg igényelhető?” kérdéshez tartozó választ használjuk,
    # hogy ne keveredjen össze a támogatási intenzitással.
    advance_percent, advance_max = _extract_advance_fields(clean_text)
    data["advance_percent"] = advance_percent
    data["advance_max"] = advance_max

    # --- Önerő % ---
    data["own_fund_percent"] = _extract_own_fund_percent(clean_text)

    if "nem szükséges önerő" in lower or "önerő nélkül" in lower:
        data["own_fund_required"] = "nem"
    elif "önerő" in lower or "saját forrás" in lower:
        data["own_fund_required"] = "igen"
    else:
        data["own_fund_required"] = None

    # Konzorcium: ha tiltás szerepel, nem
    if re.search(r"konzorcium[^\n]{0,80}(nem|nincs|nem támogatható|nem lehetséges)", lower):
        data["consortium_allowed"] = "nem"
    elif "konzorcium" in lower:
        data["consortium_allowed"] = "igen"
    else:
        data["consortium_allowed"] = "nem"

    support_logic = _extract_support_logic_text(clean_text)
    data["support_logic_text"] = support_logic
    if support_logic and "visszatérítendő" in support_logic.lower() and "vissza nem térítendővé" in support_logic.lower():
        data["support_type"] = "feltételesen vissza nem térítendő"
    elif "feltételesen vissza nem térítendő" in lower:
        data["support_type"] = "feltételesen vissza nem térítendő"
    elif "vissza nem térítendő" in lower:
        data["support_type"] = "vissza nem térítendő"
    elif "kölcsön" in lower or "hitel" in lower:
        data["support_type"] = "kölcsön / hitel"
    else:
        data["support_type"] = None

    # Projekt időtartam
    match = re.search(r"(\d{1,3})\s*hónap", lower)
    data["project_duration_months"] = int(match.group(1)) if match else None

    # Min / max támogatás – egyszerű, robusztus minták
    max_match = re.search(r"(?:maximum|maximális|legfeljebb)[^\n]{0,120}?(\d[\d\s\.,]*)\s*(ft|forint|millió|mrd|milliárd|mft)", lower)
    min_match = re.search(r"(?:minimum|minimális|legalább)[^\n]{0,120}?(\d[\d\s\.,]*)\s*(ft|forint|millió|mrd|milliárd|mft)", lower)
    budget_match = re.search(r"(?:keretösszeg|rendelkezésre álló keret)[^\n]{0,160}?(\d[\d\s\.,]*)\s*(ft|forint|millió|mrd|milliárd|mft)", lower)
    data["max_support"] = _to_int_huf(max_match.group(1), max_match.group(2)) if max_match else None
    data["min_support"] = _to_int_huf(min_match.group(1), min_match.group(2)) if min_match else None
    data["total_budget_huf"] = _to_int_huf(budget_match.group(1), budget_match.group(2)) if budget_match else None

    data.setdefault("submission_start", None)
    data.setdefault("submission_end", None)
    # Kereshető szövegrészletek: kedvezményezetti kör, tevékenységek, helyszín
    beneficiary = _extract_beneficiary_text(clean_text) or _extract_section(clean_text, [
        "kedvezményezettek köre", "jogosultak köre", "támogatást igénylők köre",
        "ki nyújthat be támogatási kérelmet", "támogatási kérelmet nyújthatnak be"
    ], max_chars=2000)
    activity = _extract_activity_text(clean_text) or _extract_section(clean_text, [
        "támogatható tevékenységek", "támogatható tevékenység",
        "önállóan támogatható", "választható tevékenység", "tevékenységek"
    ], max_chars=1600)
    location = _extract_location_text(clean_text) or _extract_section(clean_text, [
        "megvalósítás helyszíne", "területi korlátozás", "földrajzi terület",
        "a projekt megvalósítási területe"
    ], max_chars=1600)

    data["beneficiary_text"] = _clean_beneficiary_answer(beneficiary, max_chars=1200)
    data["activity_text"] = activity
    data["indicator_text"] = _extract_indicator_text(clean_text)
    data["activity_count"] = len(re.findall(r"(?:önállóan|választható|kötelezően)?\s*támogatható tevékenység", lower)) or None
    data["project_count"] = data.get("project_count")
    data["location_text"] = location

    return data
