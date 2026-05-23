"""Magyar Mistral/Ollama alapú indikátor- és eredményességi összefoglaló.

Javítások:
- hosszabb timeout: alapértelmezés 600 mp;
- egyetlen LLM-hívás PDF-enként, nem két lassú hívás;
- rövidített, releváns bemenet a teljes PDF helyett;
- magyar nyelvű, determinisztikus prompt;
- egyértelmű diagnosztika, ha Ollama/Mistral nem elérhető.
"""
from __future__ import annotations

import os
import re
import requests
import logging

logger = logging.getLogger(__name__)

OLLAMA_HOST = os.environ.get("OLLAMA_HOST", "127.0.0.1:11434")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "mistral")
OLLAMA_TIMEOUT = int(os.environ.get("OLLAMA_TIMEOUT", "600"))
MAX_INPUT_CHARS = int(os.environ.get("LLM_INPUT_CHARS", "9000"))
PROMPT_VERSION = "v5-mistral-hu-onecall"

KEY_SECTIONS = [
    "a felhívás célja", "cél", "eredményesség", "indikátor", "mérföldkő",
    "támogatható tevékenys", "kedvezményezett", "elszámolható költség",
    "támogatás formája", "előleg", "önerő", "fenntartás", "területi",
]


def is_ollama_available() -> tuple[bool, str]:
    try:
        r = requests.get(f"http://{OLLAMA_HOST}/api/tags", timeout=8)
        r.raise_for_status()
        names = [m.get("name", "") for m in r.json().get("models", [])]
        return True, ", ".join(names) or "Ollama fut, de nincs letöltött modell."
    except Exception as e:
        return False, str(e)


def _normalize_text(text: str) -> str:
    text = re.sub(r"[ \t]+", " ", text or "")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def select_relevant_text(text: str, max_chars: int = MAX_INPUT_CHARS) -> str:
    """A teljes PDF helyett cél/indikátor/kockázat szempontból releváns részeket ad át."""
    clean = _normalize_text(text)
    if len(clean) <= max_chars:
        return clean

    lines = [ln.strip() for ln in clean.splitlines() if ln.strip()]
    selected: list[str] = []

    # eleje: cím, cél, fő adatok sokszor itt vannak
    head = "\n".join(lines[:90])
    selected.append(head)

    # releváns szakaszok környezettel
    lower_lines = [ln.lower() for ln in lines]
    taken = set(range(min(90, len(lines))))
    for i, ln in enumerate(lower_lines):
        if any(k in ln for k in KEY_SECTIONS):
            for j in range(max(0, i - 2), min(len(lines), i + 8)):
                if j not in taken:
                    selected.append(lines[j])
                    taken.add(j)
        if sum(len(x) for x in selected) >= max_chars:
            break

    joined = "\n".join(selected)
    return joined[:max_chars]


def build_prompt(text: str) -> str:
    selected = select_relevant_text(text)
    return f"""
Te magyar nyelvű EU-s pályázati és támogatás-ellenőrzési szakértő vagy.
KIZÁRÓLAG magyarul válaszolj. Ne találj ki adatot; ha nincs adat, írd azt, hogy „nincs egyértelműen azonosítható adat”.

Készíts vezetői szintű, de szakmai indikátor- és eredményességi elemzést az alábbi pályázati felhívásról.

Kért struktúra:
1. FELHÍVÁS CÉLJA – 2-4 mondat.
2. NEVESÍTETT INDIKÁTOROK – felsorolásban add meg az indikátorkódokat és neveket (például RCO01, RCR19, RCR25). Ne célokat írj ide, hanem csak a szövegben szereplő tényleges indikátorokat.
3. CÉL–INDIKÁTOR ÖSSZHANG – értékeld: IGEN / RÉSZBEN / NEM / NEM MEGÍTÉLHETŐ, rövid indoklással.
4. ELLENŐRZÉSI KOCKÁZATOK – 3-5 pontban, különösen előleg, önerő, fenntartás, területi célzás, indikátor-mérhetőség alapján.
5. RÖVID VEZETŐI ÖSSZEGZÉS – 3 mondat.

Felhívás releváns szövegrészlete:
{selected}
""".strip()


def clean_llm_output(text: str) -> str:
    if not text:
        return "Az LLM nem adott használható választ."
    cleaned = text.strip()
    cleaned = cleaned.replace("Sure, here's", "").replace("Here is", "")
    lines = [line.rstrip() for line in cleaned.splitlines() if line.strip()]
    return "\n".join(lines).strip() or "Az LLM nem adott használható választ."


def _call_ollama(prompt: str, model: str = DEFAULT_MODEL) -> str | None:
    try:
        response = requests.post(
            f"http://{OLLAMA_HOST}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "num_predict": 650,
                    "num_ctx": 8192,
                    "repeat_penalty": 1.12,
                },
            },
            timeout=(10, OLLAMA_TIMEOUT),
        )
        response.raise_for_status()
        raw = response.json().get("response", "").strip()
        return raw if raw else None
    except Exception as e:
        logger.warning("Ollama/Mistral nem elérhető vagy időtúllépés történt: %s", e)
        return None


def generate_llm_indicator_material(text: str, model: str = DEFAULT_MODEL) -> str:
    ok, info = is_ollama_available()
    if not ok:
        return (
            "LLM nem elérhető – az Ollama szerver nem válaszol. "
            f"Részlet: {info}. Indítsd: ollama serve; modell: ollama pull mistral."
        )
    prompt = build_prompt(text)
    result = _call_ollama(prompt, model=model)
    if not result:
        return (
            "LLM nem elérhető – a Mistral nem adott választ a beállított időkorláton belül. "
            "Javaslat: OLLAMA_TIMEOUT=900 python -m app.ingest vagy gyorsabb modell: OLLAMA_MODEL=llama3.2:3b."
        )
    return clean_llm_output(result)


def generate_stable_summary(text: str, call_code: str = "", title: str = "", **kwargs) -> str:
    return generate_llm_indicator_material(text)
