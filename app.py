"""
app.py – Streamlit UI for AI Schema Healing System v2.1.1
Color palette: Black · Gold · White · Charcoal
"""

import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from uuid import uuid4

import pandas as pd
import streamlit as st

from config import APP_TITLE, APP_VERSION, MAX_UPLOAD_MB, REPORT_DIR, UPLOAD_DIR
from logger import logger
from schema_healer import HealingResult, check_ollama, heal_schema
from utils import build_comparison_df, read_expected_schema, validate_csv_header
from validator import ValidationReport

# ── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title=APP_TITLE,
    page_icon="🧠",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS  ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family:'Inter',sans-serif; }

/* Background */
.stApp {
    background: radial-gradient(ellipse at top left,#1a1400 0%,#0a0a0a 55%,#0d0d0d 100%);
    min-height:100vh;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background:linear-gradient(180deg,#0f0f0f 0%,#111100 100%);
    border-right:1px solid rgba(201,165,71,0.2);
}

/* Metric cards */
[data-testid="stMetric"] {
    background:rgba(201,165,71,0.06);
    border:1px solid rgba(201,165,71,0.22);
    border-radius:14px;
    padding:1rem 1.2rem;
    transition:all 0.2s ease;
}
[data-testid="stMetric"]:hover {
    border-color:rgba(201,165,71,0.55);
    background:rgba(201,165,71,0.1);
}
[data-testid="stMetricValue"] { color:#C9A547; font-weight:800; font-size:1.9rem; }
[data-testid="stMetricLabel"] { color:#888; font-size:0.78rem; text-transform:uppercase; letter-spacing:.05em; }

/* Section headers */
.sh {
    display:flex;align-items:center;gap:10px;
    background:linear-gradient(90deg,rgba(201,165,71,0.12),transparent);
    border-left:3px solid #C9A547;
    padding:.55rem 1rem;
    border-radius:0 8px 8px 0;
    margin-bottom:1rem;
    color:#F0E6C8;
    font-weight:700;
    font-size:1rem;
    letter-spacing:.02em;
}

/* Badges */
.b-exact  {background:#145A32;color:#58D68D;padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700;}
.b-norm   {background:#1A4A6B;color:#5DADE2;padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700;}
.b-fuzzy  {background:#6E2F00;color:#F39C12;padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700;}
.b-ai     {background:#4A235A;color:#D7BDE2;padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700;}
.b-none   {background:#2C2C2C;color:#888;   padding:2px 10px;border-radius:999px;font-size:.7rem;font-weight:700;}

/* Pills */
.pill-ok   {background:#0B3D25;color:#58D68D;border:1px solid #1E8449;padding:3px 12px;border-radius:999px;font-size:.8rem;}
.pill-err  {background:#4A0000;color:#F1948A;border:1px solid #922B21;padding:3px 12px;border-radius:999px;font-size:.8rem;}

/* Heal button */
.stButton>button {
    background:linear-gradient(135deg,#C9A547,#A07830);
    color:#0a0a0a !important;
    border:none;border-radius:10px;
    font-weight:800;font-size:1rem;
    padding:.65rem 1.5rem;
    transition:all .2s ease;
    box-shadow:0 4px 18px rgba(201,165,71,.35);
    width:100%;
}
.stButton>button:hover {
    transform:translateY(-2px);
    box-shadow:0 8px 28px rgba(201,165,71,.55);
}

/* Download buttons */
.stDownloadButton>button {
    background:linear-gradient(135deg,#1a1a00,#2a2200) !important;
    color:#C9A547 !important;
    border:1px solid rgba(201,165,71,.45) !important;
    border-radius:8px !important;
    font-weight:600 !important;
    box-shadow:0 3px 12px rgba(0,0,0,.4) !important;
    transition:all .2s ease !important;
}
.stDownloadButton>button:hover {
    border-color:#C9A547 !important;
    box-shadow:0 5px 18px rgba(201,165,71,.3) !important;
}

/* Expanders */
[data-testid="stExpander"] {
    background:rgba(255,255,255,.02);
    border:1px solid rgba(201,165,71,.15);
    border-radius:10px;
}

/* Divider */
hr { border-color:rgba(201,165,71,.15) !important; }

/* DataFrames */
[data-testid="stDataFrame"] { border-radius:10px; overflow:hidden; }

/* Header text */
.gold-text {
    background:linear-gradient(90deg,#F0D060,#C9A547,#A07830,#C9A547);
    -webkit-background-clip:text;
    -webkit-text-fill-color:transparent;
    background-clip:text;
    font-weight:800;
}

/* Brain logo */
.brain-logo {
    width:54px;height:54px;
    background:linear-gradient(135deg,#C9A547,#A07830);
    border-radius:50%;
    display:flex;align-items:center;justify-content:center;
    font-size:1.8rem;
    box-shadow:0 0 20px rgba(201,165,71,.4),0 0 40px rgba(201,165,71,.15);
    animation:pulse 3s ease-in-out infinite;
}
@keyframes pulse {
    0%,100%{box-shadow:0 0 20px rgba(201,165,71,.4),0 0 40px rgba(201,165,71,.15);}
    50%{box-shadow:0 0 30px rgba(201,165,71,.7),0 0 60px rgba(201,165,71,.3);}
}

/* Save badge */
.saved-badge {
    display:inline-flex;align-items:center;gap:6px;
    background:rgba(201,165,71,.1);border:1px solid rgba(201,165,71,.3);
    color:#C9A547;padding:4px 12px;border-radius:6px;font-size:.8rem;
}
</style>
""", unsafe_allow_html=True)


# ── Helper: persist files to disk ────────────────────────────────────────────

def _save_upload(file_obj, subdir: Path) -> Path:
    """Persist an upload using a generated filename, never the supplied path."""
    safe_name = Path(file_obj.name).name
    suffix = Path(safe_name).suffix.lower() or ".csv"
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    dest = subdir / f"{ts}_{uuid4().hex[:8]}{suffix}"
    dest.write_bytes(file_obj.getvalue())
    return dest


def _save_reports(result: HealingResult, val: ValidationReport) -> dict:
    ts = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + uuid4().hex[:8]
    paths = {}

    csv_path = REPORT_DIR / f"{ts}_updated_data.csv"
    csv_path.write_text(result.healed_df.to_csv(index=False), encoding="utf-8")
    paths["csv"] = csv_path

    map_path = REPORT_DIR / f"{ts}_column_mapping.json"
    map_path.write_text(json.dumps(result.mapping, indent=2), encoding="utf-8")
    paths["mapping"] = map_path

    val_path = REPORT_DIR / f"{ts}_validation_report.json"
    val_path.write_text(json.dumps(val.to_dict(), indent=2), encoding="utf-8")
    paths["validation"] = val_path

    logger.info("Reports saved | %s", {k: str(v) for k, v in paths.items()})
    return paths


# ── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(
        "<div style='display:flex;align-items:center;gap:12px;margin-bottom:4px'>"
        "<div class='brain-logo'>🧠</div>"
        "<div><div style='color:#C9A547;font-weight:800;font-size:1.15rem'>Schema Healer</div>"
        f"<div style='color:#555;font-size:.75rem'>v{APP_VERSION}</div></div></div>",
        unsafe_allow_html=True,
    )
    st.divider()

    st.markdown("<span style='color:#C9A547;font-weight:700;font-size:.85rem'>⚙ HOW IT WORKS</span>",
                unsafe_allow_html=True)
    stages = [
        ("1", "Exact Match",      "#145A32"),
        ("2", "Normalised Match", "#1A4A6B"),
        ("3", "Fuzzy Match",      "#6E2F00"),
        ("4", "AI / LLM Match",   "#4A235A"),
        ("5", "Validation",       "#6B1A1A"),
        ("6", "Reconstruction",   "#1A3A3A"),
    ]
    for num, label, color in stages:
        st.markdown(
            f"<div style='display:flex;align-items:center;gap:10px;margin:7px 0'>"
            f"<span style='background:{color};border:1px solid rgba(201,165,71,.3);color:#C9A547;"
            f"border-radius:50%;width:24px;height:24px;display:flex;align-items:center;"
            f"justify-content:center;font-size:.7rem;font-weight:800;flex-shrink:0'>{num}</span>"
            f"<span style='color:#bbb;font-size:.83rem'>{label}</span></div>",
            unsafe_allow_html=True,
        )

    st.divider()
    ollama_ok = check_ollama()
    st.markdown(
        "<span class='pill-ok'>◉ Ollama Online</span>" if ollama_ok
        else "<span class='pill-err'>◉ Ollama Offline</span>",
        unsafe_allow_html=True,
    )
    if not ollama_ok:
        st.caption("Stages 1–3 still work offline.")


# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(
    "<div style='display:flex;align-items:center;gap:16px;margin-bottom:4px'>"
    "<div class='brain-logo' style='width:62px;height:62px;font-size:2rem'>🧠</div>"
    "<div><h1 class='gold-text' style='margin:0;font-size:2.3rem'>AI Schema Healing System</h1>"
    "<p style='color:#555;margin:0;font-size:.9rem'>Local-first schema reconciliation powered by deterministic matching and optional AI</p>"
    "</div></div>",
    unsafe_allow_html=True,
)
st.divider()


# ── File upload ───────────────────────────────────────────────────────────────
st.markdown("<div class='sh'>📂 Upload Files</div>", unsafe_allow_html=True)
col_up1, col_up2 = st.columns(2)

with col_up1:
    st.markdown("<p style='color:#888;font-size:.83rem;margin-bottom:5px'>Expected Schema CSV — one column name per row</p>",
                unsafe_allow_html=True)
    expected_file = st.file_uploader("Expected Schema", type=["csv"],
                                     label_visibility="collapsed", key="exp_upload")

with col_up2:
    st.markdown("<p style='color:#888;font-size:.83rem;margin-bottom:5px'>Incoming Data CSV — the file with schema drift</p>",
                unsafe_allow_html=True)
    data_file = st.file_uploader("Incoming Data", type=["csv"],
                                  label_visibility="collapsed", key="data_upload")

if not (expected_file and data_file):
    st.markdown(
        "<div style='text-align:center;padding:3rem;color:#555;font-size:.95rem'>"
        "⬆ Upload both CSV files above to begin schema healing</div>",
        unsafe_allow_html=True,
    )
    # Clear stale session results when files are removed
    st.session_state.pop("result", None)
    st.session_state.pop("elapsed", None)
    st.session_state.pop("saved_paths", None)
    st.stop()

# ── Parse uploads & save to uploads/ ─────────────────────────────────────────
try:
    if expected_file.size > MAX_UPLOAD_MB * 1024 * 1024 or data_file.size > MAX_UPLOAD_MB * 1024 * 1024:
        raise ValueError(f"Each CSV must be no larger than {MAX_UPLOAD_MB} MB")
    validate_csv_header(expected_file.getvalue(), expected_file.name)
    validate_csv_header(data_file.getvalue(), data_file.name)
    expected_file.seek(0)
    data_file.seek(0)
    expected_df = pd.read_csv(expected_file)
    incoming_df = pd.read_csv(data_file)
    if incoming_df.empty and len(incoming_df.columns) == 0:
        raise ValueError("Incoming CSV must contain a header row")
except (ValueError, pd.errors.ParserError, UnicodeDecodeError) as e:
    st.error(f"Unable to read CSV files: {e}")
    st.stop()
except Exception as e:
    st.error(f"Unexpected CSV loading error: {e}")
    st.stop()

# Save raw uploads to disk (only when files change)
upload_digest = hashlib.sha256(expected_file.getvalue() + b"\0" + data_file.getvalue()).hexdigest()
upload_key = f"{expected_file.name}_{data_file.name}_{upload_digest}"
if st.session_state.get("upload_key") != upload_key:
    expected_file.seek(0)
    data_file.seek(0)
    _save_upload(expected_file, UPLOAD_DIR)
    _save_upload(data_file, UPLOAD_DIR)
    expected_file.seek(0)
    data_file.seek(0)
    # Re-parse after seek
    expected_df = pd.read_csv(expected_file)
    incoming_df = pd.read_csv(data_file)
    st.session_state["upload_key"] = upload_key
    st.session_state.pop("result", None)   # new files → clear old result
    st.session_state.pop("elapsed", None)
    st.session_state.pop("saved_paths", None)
    logger.info("Uploads saved | schema=%s data=%s", expected_file.name, data_file.name)

try:
    expected_schema = read_expected_schema(expected_df)
    actual_cols = list(incoming_df.columns)
    if len(actual_cols) != len(set(actual_cols)):
        raise ValueError("Incoming CSV contains duplicate column names")
except ValueError as exc:
    st.error(str(exc))
    st.stop()
st.divider()

# ── Overview metrics ──────────────────────────────────────────────────────────
st.markdown("<div class='sh'>📊 Schema Overview</div>", unsafe_allow_html=True)
m1, m2, m3, m4 = st.columns(4)
m1.metric("Expected Columns",    len(expected_schema))
m2.metric("Incoming Columns",    len(actual_cols))
m3.metric("Incoming Rows",       f"{len(incoming_df):,}")
m4.metric("Pre-Existing Matches", len(set(expected_schema) & set(actual_cols)))
st.divider()

# ── Data preview ──────────────────────────────────────────────────────────────
st.markdown("<div class='sh'>🔍 Data Preview</div>", unsafe_allow_html=True)
pc1, pc2 = st.columns(2)
with pc1:
    st.markdown("<span style='color:#C9A547;font-weight:600'>Expected Schema</span>", unsafe_allow_html=True)
    st.dataframe(pd.DataFrame({"Expected Column": expected_schema}),
                 width="stretch", height=240)
with pc2:
    st.markdown("<span style='color:#C9A547;font-weight:600'>Incoming Data (first 5 rows)</span>",
                unsafe_allow_html=True)
    st.dataframe(incoming_df.head(), width="stretch", height=240)
st.divider()

with st.expander("📋  Side-by-Side Column Comparison", expanded=False):
    st.dataframe(build_comparison_df(expected_schema, actual_cols), width="stretch")

st.divider()

# ── Heal button ───────────────────────────────────────────────────────────────
if not ollama_ok:
    st.warning("Ollama is offline — Stages 1–3 (exact, normalised, fuzzy) will still run.")

heal_btn = st.button("🚀  Run Schema Healing", width="stretch")

# Execute healing only when button clicked (NOT on download-triggered reruns)
if heal_btn:
    with st.spinner("Running schema healing pipeline…"):
        try:
            t0 = time.perf_counter()
            result = heal_schema(incoming_df, expected_schema)
            elapsed = time.perf_counter() - t0
        except Exception as exc:
            logger.exception("Pipeline error: %s", exc)
            st.error(f"❌ Schema healing failed: {exc}")
            st.stop()

    # Persist to reports/ and save everything in session_state
    saved_paths = _save_reports(result, result.validation_report)
    st.session_state["result"]      = result
    st.session_state["elapsed"]     = elapsed
    st.session_state["saved_paths"] = saved_paths

# ── Render results from session_state (survives download reruns) ──────────────
if "result" not in st.session_state:
    st.stop()

result: HealingResult      = st.session_state["result"]
elapsed: float             = st.session_state["elapsed"]
saved_paths: dict          = st.session_state["saved_paths"]
val: ValidationReport      = result.validation_report

if val.is_valid:
    st.success("✅  Schema healing completed successfully!")
else:
    st.warning("⚠️  Completed with warnings — review the validation report below.")

st.divider()

# ── Strategy summary ──────────────────────────────────────────────────────────
st.markdown("<div class='sh'>🎯 Matching Strategy Summary</div>", unsafe_allow_html=True)
s = result.strategy_summary
sc1, sc2, sc3, sc4, sc5, sc6 = st.columns(6)
sc1.metric("⚡ Exact",       s.get("exact", 0))
sc2.metric("🔤 Normalised",  s.get("normalized", 0))
sc3.metric("🔀 Fuzzy",       s.get("fuzzy", 0))
sc4.metric("🤖 AI",          s.get("ai", 0))
sc5.metric("❓ Unmatched",   s.get("unmatched", 0))
sc6.metric("⏱ Time (s)",    f"{elapsed:.2f}")
st.divider()

# ── Mapping table ─────────────────────────────────────────────────────────────
st.markdown("<div class='sh'>🗺️  Column Mapping Detail</div>", unsafe_allow_html=True)

strategy_label = {
    "exact":      "Exact",
    "normalized": "Normalised",
    "fuzzy":      "Fuzzy",
    "ai":         "AI",
}
mapping_rows = [
    {
        "Actual Column":   m.source_col,
        "Expected Column": m.target_col,
        "Strategy":        strategy_label.get(m.strategy, m.strategy.capitalize()),
        "Confidence":      f"{m.confidence:.0%}",
        "Fuzzy Score":     f"{m.fuzzy_score:.1f}" if m.fuzzy_score else "—",
    }
    for m in result.match_report.matched
]
for col in result.match_report.unmatched_expected:
    mapping_rows.append({
        "Actual Column": "—", "Expected Column": col,
        "Strategy": "Unmatched", "Confidence": "0%", "Fuzzy Score": "—",
    })
st.dataframe(pd.DataFrame(mapping_rows), width="stretch")
st.divider()

# ── Validation ────────────────────────────────────────────────────────────────
st.markdown("<div class='sh'>🛡️  Validation Report</div>", unsafe_allow_html=True)
vc1, vc2, vc3, vc4 = st.columns(4)
vc1.metric("Missing Columns",    len(val.missing_expected))
vc2.metric("Duplicate Mappings", len(val.duplicate_mappings))
vc3.metric("Unmapped Actuals",   len(val.unmapped_actual))
vc4.metric("Extra Columns",      len(val.extra_actual))

for err in val.errors:
    st.error(f"❌ {err}")
for warn in val.warnings:
    st.warning(f"⚠️ {warn}")
if not val.errors and not val.warnings:
    st.success("All validation checks passed.", icon="✅")

with st.expander("📄  Full Validation Details"):
    st.json(val.to_dict())
st.divider()

# ── Healed dataset preview ────────────────────────────────────────────────────
st.markdown("<div class='sh'>📦  Healed Dataset</div>", unsafe_allow_html=True)
if val.unmapped_actual:
    st.info("The output retains the expected schema only. Unmapped incoming columns are listed in the validation report and are not included in this CSV.")
st.dataframe(result.healed_df.head(20), width="stretch")

# Show where reports were saved
st.markdown(
    "<div class='saved-badge'>💾 Reports auto-saved to <code>reports/</code></div>",
    unsafe_allow_html=True,
)
st.divider()

# ── Downloads (session_state keeps results alive across reruns) ───────────────
st.markdown("<div class='sh'>⬇️  Downloads</div>", unsafe_allow_html=True)
dl1, dl2, dl3 = st.columns(3)

with dl1:
    st.download_button(
        "⬇️  Healed Data (CSV)",
        result.healed_df.to_csv(index=False).encode("utf-8"),
        "updated_data.csv", "text/csv",
        width="stretch",
        key="dl_csv",
    )
with dl2:
    st.download_button(
        "⬇️  Column Mapping (JSON)",
        json.dumps(result.mapping, indent=2),
        "column_mapping.json", "application/json",
        width="stretch",
        key="dl_map",
    )
with dl3:
    st.download_button(
        "⬇️  Validation Report (JSON)",
        json.dumps(val.to_dict(), indent=2),
        "validation_report.json", "application/json",
        width="stretch",
        key="dl_val",
    )

logger.info("Session rendered | rows=%d cols=%d", *result.healed_df.shape)