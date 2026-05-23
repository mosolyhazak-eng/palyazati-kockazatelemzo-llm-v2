import html
import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(layout="wide", page_title="Pályázati kockázatelemző")

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "grants.db"


# -----------------------------------------------------------------------------
# Stílus
# -----------------------------------------------------------------------------
st.markdown(
    """
    <style>
    .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
    h1 {font-size: 2.05rem !important; margin-bottom: .25rem !important;}
    h2, h3 {margin-top: 1.2rem !important;}
    .muted {color:#667085; font-size:0.92rem;}
    .section-card {
        background:#ffffff;
        border:1px solid #e6e8ee;
        border-radius:16px;
        padding:18px 20px;
        box-shadow:0 1px 4px rgba(16,24,40,.05);
        margin-bottom:14px;
    }
    .metric-card {
        background:linear-gradient(180deg,#ffffff,#fafbff);
        border:1px solid #e6e8ee;
        border-radius:16px;
        padding:15px 16px;
        box-shadow:0 1px 4px rgba(16,24,40,.05);
        min-height:92px;
    }
    .metric-label {color:#667085;font-size:.78rem;margin-bottom:6px;}
    .metric-value {font-size:1.32rem;font-weight:700;color:#101828;}
    .badge {
        display:inline-block;
        border-radius:999px;
        padding:4px 10px;
        font-size:.78rem;
        font-weight:700;
        line-height:1.2;
        margin-right:6px;
    }
    .badge-low {background:#d1fadf;color:#05603a;}
    .badge-mid {background:#fef0c7;color:#93370d;}
    .badge-high {background:#fee4e2;color:#b42318;}
    .badge-crit {background:#d92d20;color:white;}
    .text-box {
        background:#f9fafb;
        border:1px solid #eaecf0;
        border-radius:14px;
        padding:14px 16px;
        line-height:1.55;
        color:#1d2939;
        margin-bottom:10px;
    }
    .small-table table {font-size:12.5px !important; table-layout:auto;}
    .nowrap {white-space:nowrap;}
    .wide-col {min-width:170px;}
    .stDataFrame {border:1px solid #e6e8ee;border-radius:14px;overflow:hidden;}
    div[data-testid="stMetricValue"] {font-size:1.15rem;}
    </style>
    """,
    unsafe_allow_html=True,
)


# -----------------------------------------------------------------------------
# Segédfüggvények
# -----------------------------------------------------------------------------
def load_data():
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM grants", conn)
    conn.close()
    return df


def is_missing(x):
    return x is None or str(x).strip().lower() in ["", "nan", "none", "nincs adat", "ismeretlen", "—", "-"]


def fmt(x, suffix=""):
    if is_missing(x):
        return "—"
    try:
        v = float(x)
        return f"{int(v)}{suffix}" if v == int(v) else f"{v:.1f}{suffix}"
    except Exception:
        return str(x)


def fmt_huf(x):
    if is_missing(x):
        return "—"
    try:
        v = float(x)
        if v >= 1_000_000_000:
            return f"{v/1e9:.2f} Mrd Ft"
        if v >= 1_000_000:
            return f"{v/1e6:.0f} M Ft"
        return f"{v:,.0f} Ft".replace(",", " ")
    except Exception:
        return str(x)


def fmt_support(min_val, max_val):
    min_str = fmt_huf(min_val)
    max_str = fmt_huf(max_val)
    if min_str == "—" and max_str == "—":
        return "—"
    if min_str == "—":
        return max_str
    return f"{min_str} – {max_str}"


def clean_display_text(x, max_chars=1200):
    if is_missing(x):
        return "—"
    txt = str(x).replace("\n", " ")
    txt = " ".join(txt.split())
    if len(txt) > max_chars:
        return txt[:max_chars].rstrip() + "…"
    return txt


def short_text(x, max_chars=70):
    if is_missing(x):
        return "—"
    txt = clean_display_text(x, max_chars=max_chars)
    return txt


def risk_level(val):
    return str(val).strip().lower()


def risk_badge(val):
    v = risk_level(val)
    cls = {
        "alacsony": "badge-low",
        "közepes": "badge-mid",
        "magas": "badge-high",
        "kiemelt": "badge-crit",
    }.get(v, "badge-mid")
    label = html.escape(str(val if not is_missing(val) else "ismeretlen"))
    return f"<span class='badge {cls}'>{label}</span>"


def yes_no(x):
    if is_missing(x):
        return "—"
    s = str(x).strip().lower()
    if s in ["igen", "true", "1", "yes"]:
        return "igen"
    if s in ["nem", "false", "0", "no"]:
        return "nem"
    return str(x)


def own_fund_label(row):
    percent = row.get("own_fund_percent")
    required = yes_no(row.get("own_fund_required"))
    if not is_missing(percent):
        return f"min. {fmt(percent, '%')}"
    if required != "—":
        return required
    return "—"


def advance_label(row):
    adv = row.get("advance_percent")
    adv_max = row.get("advance_max")
    if is_missing(adv):
        return "—"
    s = fmt(adv, "%")
    if not is_missing(adv_max):
        s += f" / max. {fmt_huf(adv_max)}"
    return s


def render_metric_card(label, value, note=None):
    note_html = f"<div class='muted'>{html.escape(str(note))}</div>" if note else ""
    st.markdown(
        f"""
        <div class='metric-card'>
          <div class='metric-label'>{html.escape(str(label))}</div>
          <div class='metric-value'>{html.escape(str(value))}</div>
          {note_html}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_text_box(title, text, max_chars=1400):
    if is_missing(text):
        return
    st.markdown(f"**{title}**")
    st.markdown(
        f"<div class='text-box'>{html.escape(clean_display_text(text, max_chars=max_chars))}</div>",
        unsafe_allow_html=True,
    )


def split_to_items(text, max_items=12):
    if is_missing(text):
        return []
    txt = clean_display_text(text, max_chars=3500)
    markers = ["▪", "•", "\uf0a7", "– ", " - "]
    for marker in markers:
        txt = txt.replace(marker, "|||" + marker.strip())
    parts = [p.strip(" ;,.") for p in txt.split("|||") if len(p.strip()) > 6]
    # ha nem voltak felsorolásjelek, óvatosan mondatokra bontjuk
    if len(parts) <= 1:
        parts = [p.strip(" ;,.") for p in txt.split(". ") if len(p.strip()) > 18]
    return parts[:max_items]


def render_items(title, text, max_items=10):
    items = split_to_items(text, max_items=max_items)
    if not items:
        return
    st.markdown(f"**{title}**")
    for item in items:
        st.markdown(f"- {item}")


def render_html_table(df, right_cols=None, risk_col=None):
    if df.empty:
        st.info("Nincs találat.")
        return
    right_cols = right_cols or []
    html_table = "<div class='small-table'><table style='width:100%;border-collapse:collapse;font-size:12.5px'><tr>"
    for col in df.columns:
        html_table += f"<th style='border:1px solid #ddd;padding:8px;background:#f8fafc;text-align:left'>{html.escape(str(col))}</th>"
    html_table += "</tr>"
    for _, row in df.iterrows():
        html_table += "<tr>"
        for col in df.columns:
            val = row[col]
            align = "right" if col in right_cols else "left"
            nowrap = col in right_cols or col in ["Támogatás", "Önerő", "Előleg", "Keretösszeg", "Időtart.", "Időtartam"]
            min_width = "min-width:180px;" if col in ["Támogatási logika", "Kedvezményezettek", "Cím"] else ""
            ws = "white-space:nowrap;" if nowrap else ""
            style = f"padding:8px;border:1px solid #e5e7eb;text-align:{align};vertical-align:top;{min_width}{ws}"
            if risk_col and col == risk_col:
                cell = risk_badge(val)
            else:
                cell = html.escape(str(val))
                if nowrap:
                    cell = cell.replace(" ", "&nbsp;")
            html_table += f"<td style='{style}'>{cell}</td>"
        html_table += "</tr>"
    html_table += "</table></div>"
    st.markdown(html_table, unsafe_allow_html=True)


# -----------------------------------------------------------------------------
# Adatbetöltés
# -----------------------------------------------------------------------------
if not DB_PATH.exists():
    st.error("Az adatbázis nem található. Előbb futtasd: python -m app.ingest")
    st.stop()

df = load_data()
if df.empty:
    st.warning("Nincs adat az adatbázisban.")
    st.stop()

expected_columns = [
    "call_code", "title", "zsc_category", "risk_score", "risk_category",
    "llm_summary", "llm_demo", "advance_percent", "advance_max",
    "own_fund_required", "own_fund_percent", "consortium_allowed",
    "support_type", "max_support", "min_support", "project_duration_months",
    "project_count", "total_budget_huf", "beneficiary_text", "activity_text",
    "indicator_text", "location_text", "support_logic_text",
]
for col in expected_columns:
    if col not in df.columns:
        df[col] = None

# -----------------------------------------------------------------------------
# Oldalsáv
# -----------------------------------------------------------------------------
st.sidebar.header("Szűrők")
risk_options = ["Mind"] + sorted([x for x in df["risk_category"].dropna().astype(str).unique() if x.strip()])
risk = st.sidebar.selectbox("Kockázat", risk_options)
category_options = ["Mind"] + sorted([x for x in df["zsc_category"].dropna().astype(str).unique() if x.strip()])
category = st.sidebar.selectbox("ZSC kategória", category_options)

st.sidebar.markdown("---")
st.sidebar.markdown("**Kulcsszavas keresés**")
search_title = st.sidebar.text_input("Felhívás kód / cím")
search_beneficiary = st.sidebar.text_input("Kedvezményezett (kulcsszó)")
search_activity = st.sidebar.text_input("Tevékenység (kulcsszó)")

filtered = df.copy()
if risk != "Mind":
    filtered = filtered[filtered["risk_category"] == risk]
if category != "Mind":
    filtered = filtered[filtered["zsc_category"] == category]
if search_title:
    filtered = filtered[
        filtered["title"].astype(str).str.contains(search_title, case=False, na=False) |
        filtered["call_code"].astype(str).str.contains(search_title, case=False, na=False)
    ]
if search_beneficiary:
    filtered = filtered[
        filtered["beneficiary_text"].astype(str).str.contains(search_beneficiary, case=False, na=False) |
        filtered["title"].astype(str).str.contains(search_beneficiary, case=False, na=False)
    ]
if search_activity:
    filtered = filtered[
        filtered["activity_text"].astype(str).str.contains(search_activity, case=False, na=False) |
        filtered["title"].astype(str).str.contains(search_activity, case=False, na=False)
    ]

# -----------------------------------------------------------------------------
# Fejléc és KPI-k
# -----------------------------------------------------------------------------
st.title("Pályázati felhívás kockázati elemző")
st.markdown("<div class='muted'>PDF-felhívások strukturált feldolgozása, kockázati besorolása és magyar nyelvű LLM-alapú összefoglalása.</div>", unsafe_allow_html=True)

st.markdown("### Gyors áttekintés")
metric_cols = st.columns(5)
with metric_cols[0]:
    render_metric_card("Felhívások száma", len(filtered))
with metric_cols[1]:
    render_metric_card("ZSC kategóriák", filtered["zsc_category"].nunique())
with metric_cols[2]:
    render_metric_card("Magas kockázatú", int((filtered["risk_category"] == "magas").sum()))
with metric_cols[3]:
    render_metric_card("Kiemelt kockázatú", int((filtered["risk_category"] == "kiemelt").sum()))
with metric_cols[4]:
    total_budget = filtered["total_budget_huf"].apply(lambda x: float(x) if not is_missing(x) else 0).sum()
    render_metric_card("Összes keretösszeg", fmt_huf(total_budget) if total_budget > 0 else "—")

if len(filtered) < 10:
    st.warning("Az elemzés korlátozott számú felhívás alapján készült, ezért az eredmények elsősorban a módszertan demonstrálását szolgálják.")

# -----------------------------------------------------------------------------
# Ábrák és megállapítások
# -----------------------------------------------------------------------------
left, right = st.columns([1.25, 1])
with left:
    st.markdown("### Kockázati megoszlás")
    risk_counts = filtered["risk_category"].fillna("ismeretlen").value_counts()
    if len(risk_counts) > 1:
        st.bar_chart(risk_counts)
    else:
        st.info("Nem áll rendelkezésre elegendő változatosság az ábrázoláshoz.")
with right:
    st.markdown("### Automatikus megállapítások")
    if filtered["risk_category"].nunique() <= 1:
        st.markdown("<div class='text-box'>A jelenlegi mintában a kockázati besorolás homogén. A modell további adatokkal finomhangolható.</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='text-box'>A felhívások között eltérő kockázati szintek figyelhetők meg, ami támogatja az összehasonlító értékelést.</div>", unsafe_allow_html=True)
    top_cat = filtered["zsc_category"].mode()
    if not top_cat.empty:
        st.markdown(f"Leggyakoribb ZSC kategória: **{top_cat.iloc[0]}**")

# -----------------------------------------------------------------------------
# Táblák
# -----------------------------------------------------------------------------
st.markdown("### Összefoglaló tábla")

def fmt_support_row(row):
    return fmt_support(row.get("min_support"), row.get("max_support"))

display = pd.DataFrame({
    "Felhívás": filtered["call_code"].fillna("—"),
    "Cím": filtered["title"].apply(lambda x: short_text(x, 120)),
    "Kategória": filtered["zsc_category"].fillna("—"),
    "Támogatás": filtered.apply(fmt_support_row, axis=1),
    "Önerő": filtered.apply(own_fund_label, axis=1),
    "Előleg": filtered.apply(advance_label, axis=1),
    "Időtart.": filtered["project_duration_months"].apply(lambda x: fmt(x, " hó")),
    "Kedvezményezettek": filtered["beneficiary_text"].apply(lambda x: short_text(x, 75)),
    "Támogatási logika": filtered["support_logic_text"].apply(lambda x: short_text(x, 95)),
    "Keretösszeg": filtered["total_budget_huf"].apply(fmt_huf),
    "Pont": filtered["risk_score"].apply(fmt),
    "Kockázat": filtered["risk_category"].fillna("—"),
})
render_html_table(display, ["Támogatás", "Önerő", "Előleg", "Időtart.", "Keretösszeg", "Pont"], "Kockázat")

with st.expander("Legmagasabb kockázatú felhívások megjelenítése", expanded=True):
    top_risk = filtered.copy()
    top_risk["_num"] = pd.to_numeric(top_risk["risk_score"], errors="coerce")
    top_risk = top_risk.sort_values("_num", ascending=False).head(5)
    top_display = pd.DataFrame({
        "Felhívás": top_risk["call_code"].fillna("—"),
        "Cím": top_risk["title"].apply(lambda x: short_text(x, 140)),
        "Támogatás": top_risk.apply(fmt_support_row, axis=1),
        "Önerő": top_risk.apply(own_fund_label, axis=1),
        "Előleg": top_risk.apply(advance_label, axis=1),
        "Keretösszeg": top_risk["total_budget_huf"].apply(fmt_huf),
        "Pont": top_risk["risk_score"].apply(fmt),
        "Kockázat": top_risk["risk_category"].fillna("—"),
    })
    render_html_table(top_display, ["Támogatás", "Önerő", "Előleg", "Keretösszeg", "Pont"], "Kockázat")

# -----------------------------------------------------------------------------
# Részletes nézet
# -----------------------------------------------------------------------------
st.markdown("### Felhívás részletek")
options = filtered["call_code"].dropna().astype(str).tolist()

if not options:
    st.info("Nincs kiválasztható felhívás.")
    st.stop()

selected = st.selectbox("Válassz felhívást", options)
row = filtered[filtered["call_code"] == selected].iloc[0]

st.markdown(
    f"""
    <div class='section-card'>
      <div style='display:flex;justify-content:space-between;gap:16px;align-items:flex-start;'>
        <div>
          <div class='muted'>Kiválasztott felhívás</div>
          <h3 style='margin:0'>{html.escape(str(row.get('call_code', '—')))}</h3>
          <div>{html.escape(clean_display_text(row.get('title'), max_chars=220))}</div>
        </div>
        <div>{risk_badge(row.get('risk_category'))}<span class='badge badge-mid'>{html.escape(str(fmt(row.get('risk_score'))))} pont</span></div>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

tab1, tab2, tab3, tab4 = st.tabs(["Alapadatok", "Jogosultság és támogatási logika", "Indikátorok", "LLM elemzés"])

with tab1:
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        render_metric_card("Támogatás típusa", row.get("support_type", "—"))
    with c2:
        render_metric_card("Támogatási összeg", fmt_support(row.get("min_support"), row.get("max_support")))
    with c3:
        render_metric_card("Keretösszeg", fmt_huf(row.get("total_budget_huf")))
    with c4:
        render_metric_card("Időtartam", fmt(row.get("project_duration_months"), " hónap"))

    c5, c6, c7, c8 = st.columns(4)
    with c5:
        render_metric_card("Előleg", advance_label(row))
    with c6:
        render_metric_card("Önerő", own_fund_label(row), "önerő szükséges: " + yes_no(row.get("own_fund_required")))
    with c7:
        render_metric_card("ZSC kategória", row.get("zsc_category", "—"))
    with c8:
        render_metric_card("Kockázat", row.get("risk_category", "—"), f"pontszám: {fmt(row.get('risk_score'))}")

with tab2:
    render_text_box("Kedvezményezetti kör", row.get("beneficiary_text"), max_chars=1600)
    render_text_box("Támogatási logika", row.get("support_logic_text"), max_chars=900)
    render_items("Támogatható tevékenységek", row.get("activity_text"), max_items=12)

with tab3:
    indicators = row.get("indicator_text")
    if not is_missing(indicators):
        render_text_box("Nevesített indikátorok", indicators, max_chars=1800)
    else:
        st.info("A PDF-ből nem sikerült egyértelmű RCO/RCR indikátorkódot kinyerni.")

with tab4:
    st.markdown("#### Indikátor- és célrendszer elemzése")
    llm_demo = row.get("llm_demo")
    if llm_demo and str(llm_demo).strip() not in ["", "LLM nem elérhető", "nan", "None"]:
        sections = str(llm_demo).split("===")
        for section in sections:
            section = section.strip()
            if not section:
                continue
            lines = section.split("\n", 1)
            if len(lines) == 2:
                st.markdown(f"**{lines[0].strip()}**")
                st.markdown(f"<div class='text-box'>{html.escape(clean_display_text(lines[1].strip(), 1800))}</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div class='text-box'>{html.escape(clean_display_text(section, 1800))}</div>", unsafe_allow_html=True)
    else:
        st.info("LLM elemzés nem elérhető ehhez a felhíváshoz.")

    st.markdown("#### Kockázati összefoglaló")
    llm_summary = row.get("llm_summary")
    if llm_summary and str(llm_summary).strip() not in ["", "nan", "None"]:
        st.markdown(f"<div class='text-box'>{html.escape(clean_display_text(llm_summary, 2200))}</div>", unsafe_allow_html=True)
    else:
        st.info("Nincs kockázati összefoglaló.")
