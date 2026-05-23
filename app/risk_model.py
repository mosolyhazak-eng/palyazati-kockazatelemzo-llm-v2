"""
Kockázati modell modul – GINOP Plusz pályázatok értékelése.

A kockázat itt az IRÁNYÍTÓ HATÓSÁG / ELLENŐRZŐ SZERV szempontjából értendő:
mekkora az esélye, hogy a projekt megvalósítása során szabálytalanság,
fenntartási kötelezettség-szegés, vagy visszafizetési igény keletkezik.

Pontozási szempontok és maximális értékek:
  1. Előleg mértéke            – max 3 pont  (magas előleg = magasabb kockázat)
  2. Projekt időtartam         – max 3 pont  (hosszabb futamidő = komplexebb ellenőrzés)
  3. Maximális támogatás       – max 4 pont  (nagyobb összeg = nagyobb kitettség)
  4. Várható projektek száma   – max 3 pont  (több projekt = nagyobb portfólió kockázat)
  5. Támogatás visszafizetése  – max 3 pont  (vissza nem térítendő = nincs biztosíték)
  6. Önerő megléte             – max 3 pont  (önerő nélkül = alacsonyabb elköteleződés)
  7. Konzorcium                – max 2 pont  (több szereplő = koordinációs kockázat)
  + Hiányzó adatok büntetése implicit minden szempontnál

Maximum összesen: 21+ pont

Kategóriák:
  alacsony  :  0–5  pont
  közepes   :  6–11 pont
  magas     : 12–17 pont
  kiemelt   : 18+   pont
"""


def to_number(value, default=-1):
    """Szám-szerű értéket float-tá alakít. Ismeretlen esetén -1 (jelzi a hiányt)."""
    if value is None:
        return default
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().lower()
    if text in ["", "nincs adat", "none", "nan", "ismeretlen"]:
        return default
    text = (text.replace("ft", "").replace("%", "")
               .replace("hónap", "").replace("honap", "")
               .replace(" ", "").replace("\xa0", "")
               .replace(",", "."))
    try:
        return float(text)
    except (ValueError, TypeError):
        return default


def compute_risk(data: dict) -> tuple:
    """
    Kockázati pontszám, kategória és részletes indoklás számítása.

    Visszatér: (score: float, category: str, breakdown: dict)
      - score: összesített pontszám
      - category: 'alacsony' | 'közepes' | 'magas' | 'kiemelt'
      - breakdown: szempontonkénti részletezés magyarázattal
    """
    score = 0
    breakdown = {}

    advance = to_number(data.get("advance_percent"))
    duration = to_number(data.get("project_duration_months"))
    max_support = to_number(data.get("max_support"))
    project_count = to_number(data.get("project_count"))
    own_fund_pct = to_number(data.get("own_fund_percent"))

    support_type = str(data.get("support_type") or "").lower()
    own_fund_required = str(data.get("own_fund_required") or "").lower()
    consortium_allowed = str(data.get("consortium_allowed") or "").lower()

    # 1. Előleg mértéke
    # Magas előleg = az állam pénze már a projekt elején kint van,
    # visszakövetelés kockázata nagyobb szabálytalanság esetén.
    if advance < 0:
        pts, note = 1, "ismeretlen – nem értékelhető (1 pont büntetés)"
    elif advance >= 50:
        pts, note = 3, f"{advance:.0f}% – magas előleg, jelentős visszakövetelési kockázat"
    elif advance >= 25:
        pts, note = 2, f"{advance:.0f}% – közepes előleg"
    elif advance > 0:
        pts, note = 1, f"{advance:.0f}% – alacsony előleg"
    else:
        pts, note = 0, "nincs előleg – nincs előfinanszírozási kockázat"
    score += pts
    breakdown["előleg"] = {"pont": pts, "megjegyzés": note}

    # 2. Projekt időtartam
    # Hosszabb projekt = több elszámolási időszak, több ellenőrzési pont,
    # nagyobb esély közbülső változásokra (pl. kedvezményezett csőd).
    if duration < 0:
        pts, note = 1, "ismeretlen – nem értékelhető (1 pont büntetés)"
    elif duration >= 48:
        pts, note = 3, f"{duration:.0f} hónap – nagyon hosszú futamidő, magas megvalósítási kockázat"
    elif duration >= 24:
        pts, note = 2, f"{duration:.0f} hónap – közepes futamidő"
    elif duration >= 12:
        pts, note = 1, f"{duration:.0f} hónap – rövid futamidő"
    else:
        pts, note = 0, f"{duration:.0f} hónap – nagyon rövid projekt"
    score += pts
    breakdown["futamidő"] = {"pont": pts, "megjegyzés": note}

    # 3. Maximális támogatási összeg
    # Nagyobb összeg = nagyobb abszolút veszteség szabálytalanság esetén,
    # EU társfinanszírozás miatt multiplikált hatással.
    if max_support < 0:
        pts, note = 2, "ismeretlen – nem értékelhető (2 pont büntetés)"
    elif max_support >= 2_000_000_000:
        pts, note = 4, f"{max_support/1e9:.1f} Mrd Ft – kiemelt összeg, kötelező helyszíni ellenőrzés"
    elif max_support >= 500_000_000:
        pts, note = 3, f"{max_support/1e6:.0f} M Ft – nagy összeg"
    elif max_support >= 50_000_000:
        pts, note = 2, f"{max_support/1e6:.0f} M Ft – közepes összeg"
    elif max_support > 0:
        pts, note = 1, f"{max_support/1e6:.1f} M Ft – kis összeg"
    else:
        pts, note = 0, "0 Ft – nem értelmezhető"
    score += pts
    breakdown["max_támogatás"] = {"pont": pts, "megjegyzés": note}

    # 4. Várható projektek száma (portfólió kockázat)
    # Sok kis projekt = nehéz egyenként ellenőrizni,
    # rendszerszintű hibák könnyen elterjednek a portfólióban.
    if project_count < 0:
        pts, note = 1, "ismeretlen – nem értékelhető (1 pont büntetés)"
    elif project_count >= 300:
        pts, note = 3, f"{project_count:.0f} projekt – nagy portfólió, mintavételes ellenőrzés szükséges"
    elif project_count >= 50:
        pts, note = 2, f"{project_count:.0f} projekt – közepes portfólió"
    elif project_count > 0:
        pts, note = 1, f"{project_count:.0f} projekt – kis portfólió"
    else:
        pts, note = 0, "nincs adat / 0 projekt"
    score += pts
    breakdown["projektek_száma"] = {"pont": pts, "megjegyzés": note}

    # 5. Támogatás visszafizethetősége
    # Vissza nem térítendő: nincs törlesztési biztosíték, szabálytalanság esetén
    # csak kötelezettségszegési eljárással hajtható be.
    # Hitel: a visszafizetési kötelezettség önmagában kockázatcsökkentő.
    if not support_type or support_type in ["none", "nincs adat"]:
        pts, note = 2, "ismeretlen típus – nem értékelhető (2 pont büntetés)"
    elif "vissza nem térítendő" in support_type:
        pts, note = 3, "vissza nem térítendő – nincs visszafizetési biztosíték, EU-szabálytalanság esetén kötelezettségszegési eljárás"
    elif "hitel" in support_type or "kölcsön" in support_type:
        pts, note = 1, "hitel/kölcsön – visszafizetési kötelezettség részleges kockázatcsökkentő"
    else:
        pts, note = 1, f"egyéb típus: {support_type}"
    score += pts
    breakdown["támogatás_típusa"] = {"pont": pts, "megjegyzés": note}

    # 6. Önerő megléte
    # Önerő = a kedvezményezett saját anyagi érintettsége, ami csökkenti
    # a morális kockázatot (moral hazard). Ha nincs önerő, kevesebb a vesztenivaló.
    if own_fund_required in ["nem", "no", "false", "0"]:
        pts, note = 3, "önerő nem szükséges – alacsony elköteleződés, magasabb moral hazard"
    elif own_fund_required in ["igen", "yes", "true", "1"]:
        if own_fund_pct >= 50:
            pts, note = 0, f"{own_fund_pct:.0f}% önerő – erős elköteleződés, alacsony kockázat"
        elif own_fund_pct >= 20:
            pts, note = 1, f"{own_fund_pct:.0f}% önerő – közepes elköteleződés"
        elif own_fund_pct >= 0:
            pts, note = 2, f"{own_fund_pct:.0f}% önerő – alacsony arányú, gyenge biztosíték"
        else:
            pts, note = 1, "önerő szükséges, mértéke ismeretlen"
    else:
        pts, note = 2, "önerő ismeretlen – nem értékelhető (2 pont büntetés)"
    score += pts
    breakdown["önerő"] = {"pont": pts, "megjegyzés": note}

    # 7. Konzorcium
    # Több tag = koordinációs kockázat, felelősség megosztása,
    # vezető partner csődje esetén az egész projekt veszélybe kerülhet.
    if consortium_allowed in ["igen", "yes", "true", "1"]:
        pts, note = 2, "konzorcium lehetséges – több szereplő, koordinációs és felelősségi kockázat"
    else:
        pts, note = 0, "konzorcium nem lehetséges – egy kedvezményezett, egyértelmű felelősség"
    score += pts
    breakdown["konzorcium"] = {"pont": pts, "megjegyzés": note}

    # Kategorizálás
    if score >= 18:
        category = "kiemelt"
    elif score >= 12:
        category = "magas"
    elif score >= 6:
        category = "közepes"
    else:
        category = "alacsony"

    return score, category, breakdown
