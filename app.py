"""
app.py  —  FinanceFlow-AI  |  Dark-themed dashboard with progressive section reveal.

RUN:  py -m streamlit run app.py
"""

import os, sys, time, json
import streamlit as st
import streamlit.components.v1 as components
import plotly.graph_objects as go
import pandas as pd
from dotenv import load_dotenv
load_dotenv()

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader     import load_data
from src.variance_engine import run_variance_engine
from src.commentary      import generate_commentary
from src.report_builder  import build_report
from src                 import config

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="FinanceFlow-AI",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Brand palette  (matches logo: dark bg + teal accent) ─────────────────────
BG      = "#0B1916"
BG_CARD = "#132820"
BG_MID  = "#1A3328"
TEAL    = "#00C896"
TEAL_DIM= "#7EC8B5"
WHITE   = "#FFFFFF"
GRAY    = "#8FADA6"
RED     = "#E05252"
GREEN   = "#00C896"
BORDER  = "#1E3D30"

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ─── Reset & shell ─── */
*, *::before, *::after {{ box-sizing:border-box; }}
[data-testid="stApp"] {{
    background-color:{BG}; color:{WHITE};
    font-family:'Inter',sans-serif;
}}
[data-testid="stSidebarCollapsedControl"],
[data-testid="stSidebar"] {{ display:none!important; }}
.main .block-container {{ padding-top:0!important; max-width:1280px; }}
[data-testid="stMainBlockContainer"] {{ padding-top:0!important; max-width:1280px; }}
header[data-testid="stHeader"] {{ background:transparent; }}
#MainMenu, footer {{ visibility:hidden; }}

/* ─── ALL text & labels default to readable ─── */
p, span, label, div {{ color:{WHITE}; }}
[data-testid="stWidgetLabel"] p,
[data-testid="stWidgetLabel"] span,
label p {{ color:{TEAL_DIM}!important; font-size:.78rem!important;
           font-weight:600!important; text-transform:uppercase!important;
           letter-spacing:.07em!important; }}

/* ─── Metric cards ─── */
[data-testid="stMetric"] {{
    background:{BG_CARD}; border:1px solid {BORDER};
    border-radius:14px; padding:22px 24px;
}}
[data-testid="stMetricLabel"] p {{
    font-size:.72rem!important; color:{TEAL_DIM}!important;
    text-transform:uppercase!important; letter-spacing:.08em!important;
}}
[data-testid="stMetricValue"] {{
    font-size:1.5rem!important; font-weight:800!important; color:{WHITE}!important;
}}
[data-testid="stMetricDelta"] svg {{ display:none; }}

/* ─── Expanders — full dark fix ─── */
[data-testid="stExpander"] {{
    background:{BG_CARD}!important; border:1px solid {BORDER}!important;
    border-radius:14px!important; margin-bottom:14px!important; overflow:hidden!important;
}}
/* details element itself (Streamlit default is white) */
[data-testid="stExpander"] details {{
    background:{BG_CARD}!important;
}}
[data-testid="stExpander"] details summary {{
    background:{BG_CARD}!important; color:{WHITE}!important;
    font-size:.97rem!important; font-weight:700!important;
    padding:16px 22px!important; list-style:none!important;
    cursor:pointer!important; border-bottom:0!important;
}}
[data-testid="stExpander"] details summary:hover {{
    color:{TEAL}!important;
}}
[data-testid="stExpander"] details[open] summary {{
    border-bottom:1px solid {BORDER}!important;
}}
/* Content area */
[data-testid="stExpanderDetails"] {{
    background:{BG_CARD}!important; padding:18px 22px!important;
}}
[data-testid="stExpanderDetails"] * {{
    color:{WHITE};
}}

/* ─── Bordered container (upload cards) ─── */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background:{BG_CARD}!important;
    border:1px solid {BORDER}!important;
    border-radius:16px!important;
    padding:4px 2px!important;
    transition:border-color .25s, box-shadow .25s;
}}
[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    border-color:{TEAL}!important;
    box-shadow:0 0 0 1px rgba(0,200,150,.12), 0 4px 20px rgba(0,200,150,.07)!important;
}}

/* ─── File uploader ─── */
[data-testid="stFileUploader"] section {{
    background:{BG_MID}!important;
    border:1.5px dashed {BORDER}!important;
    border-radius:10px!important;
    transition:border-color .2s!important;
    padding:18px 14px!important;
}}
[data-testid="stFileUploader"] section:hover {{
    border-color:{TEAL}!important;
}}
/* "Browse files" button — target every possible Streamlit selector */
[data-testid="stFileUploader"] button,
[data-testid="stFileUploader"] [data-testid="baseButton-secondary"],
[data-testid="stFileUploader"] [data-testid="baseButton-primary"],
[data-testid="stFileUploaderDropzone"] button,
[data-testid="stFileUploaderDropzone"] > div > button {{
    background:transparent!important;
    background-color:transparent!important;
    color:{TEAL}!important;
    border:1.5px solid {TEAL}!important;
    border-radius:7px!important;
    font-size:.8rem!important;
    font-weight:700!important;
    padding:6px 20px!important;
    transition:all .18s!important;
    box-shadow:none!important;
}}
[data-testid="stFileUploader"] button p,
[data-testid="stFileUploader"] button span,
[data-testid="stFileUploaderDropzone"] button p,
[data-testid="stFileUploaderDropzone"] button span {{
    color:{TEAL}!important;
    font-weight:700!important;
}}
[data-testid="stFileUploader"] button:hover,
[data-testid="stFileUploaderDropzone"] button:hover {{
    background:rgba(0,200,150,.12)!important;
    background-color:rgba(0,200,150,.12)!important;
}}
/* Drag & drop instruction text */
[data-testid="stFileUploaderDropzoneInstructions"] span,
[data-testid="stFileUploaderDropzoneInstructions"] small,
[data-testid="stFileUploader"] section span,
[data-testid="stFileUploader"] section small {{
    color:{GRAY}!important;
    font-size:.78rem!important;
}}

/* ─── Primary button ─── */
[data-testid="stButton"] > button {{
    background:{TEAL}; color:#041A14; font-weight:800;
    border:none; border-radius:10px;
    padding:13px 32px; font-size:1rem;
    transition:all .2s ease; letter-spacing:.02em;
    box-shadow:0 4px 16px rgba(0,200,150,.25);
}}
[data-testid="stButton"] > button:hover {{
    background:#00B884; transform:translateY(-2px);
    box-shadow:0 8px 24px rgba(0,200,150,.4);
}}

/* ─── Download button ─── */
[data-testid="stDownloadButton"] > button {{
    background:{TEAL}; color:#041A14; font-weight:800;
    border:none; border-radius:12px;
    padding:16px 40px; font-size:1.05rem;
    transition:all .2s ease;
    box-shadow:0 4px 20px rgba(0,200,150,.3);
}}
[data-testid="stDownloadButton"] > button:hover {{
    background:#00B884; transform:translateY(-2px);
    box-shadow:0 10px 28px rgba(0,200,150,.45);
}}

/* ─── Checkbox ─── */
[data-testid="stCheckbox"] {{
    margin-top:0.6rem!important;
    padding-top:0!important;
    width:fit-content!important;
    margin-left:auto!important;
    margin-right:auto!important;
    transform:translateX(192px)!important;
}}
[data-testid="stCheckbox"] label {{
    color:{TEAL_DIM}!important; font-size:.92rem!important;
    font-weight:500!important;
}}
[data-testid="stCheckbox"] label p {{
    color:{TEAL_DIM}!important; text-transform:none!important;
    letter-spacing:normal!important; font-size:.92rem!important;
    font-weight:500!important;
}}

/* ─── Selectbox ─── */
[data-testid="stSelectbox"] > div > div {{
    background:{BG_CARD}!important; color:{WHITE}!important;
    border-color:{BORDER}!important; border-radius:9px!important;
}}
/* Dropdown popup */
[data-baseweb="popover"] ul,
[data-baseweb="menu"] {{
    background:{BG_CARD}!important;
    border:1px solid {BORDER}!important;
    border-radius:10px!important;
}}
[data-baseweb="menu"] li,
[data-baseweb="option"] {{
    background:{BG_CARD}!important;
    color:{WHITE}!important;
}}
[data-baseweb="menu"] li:hover,
[data-baseweb="option"]:hover {{
    background:{BG_MID}!important;
    color:{TEAL}!important;
}}

/* ─── Number input ─── */
[data-testid="stNumberInput"] input {{
    background:{BG_MID}!important; color:{WHITE}!important;
    border-color:{BORDER}!important; border-radius:8px!important;
    font-size:.95rem!important; font-weight:600!important;
}}
[data-testid="stNumberInput"] button {{
    background:{BG_MID}!important; color:{TEAL}!important;
    border-color:{BORDER}!important;
}}

/* ─── Alert boxes ─── */
[data-testid="stAlert"] {{ background:{BG_CARD}; border-radius:10px; }}

/* ─── Success alert ─── */
[data-testid="stAlert"][data-baseweb="notification"] {{
    background:rgba(0,200,150,.08)!important;
    border-color:{TEAL}!important; border-left-width:3px!important;
    border-radius:8px!important;
}}

/* ─── Dataframe ─── */
[data-testid="stDataFrame"] > div {{
    background:{BG_CARD}; border-radius:10px; overflow:hidden;
}}

/* ─── Caption ─── */
[data-testid="stCaptionContainer"] p,
[data-testid="stCaptionContainer"] span {{ color:{GRAY}!important; }}

/* ─── Divider ─── */
hr {{ border-color:{BORDER}; opacity:.6; }}

/* ─── Status box ─── */
[data-testid="stStatus"] {{
    background:{BG_CARD}!important; border-color:{BORDER}!important;
    border-radius:12px!important;
}}

/* ─── Animations ─── */
@keyframes fadeInUp {{
    from {{ opacity:0; transform:translateY(16px); }}
    to   {{ opacity:1; transform:translateY(0); }}
}}
@keyframes pulse {{
    0%,100% {{ opacity:.45; }}
    50%      {{ opacity:1; }}
}}
@keyframes shimmer {{
    0%   {{ background-position:-200% center; }}
    100% {{ background-position:200% center; }}
}}

/* ─── Working message ─── */
.working-msg {{
    text-align:center; padding:40px 20px;
    color:{TEAL_DIM}; font-size:.9rem;
    letter-spacing:.05em; font-weight:500;
    animation:pulse 1.6s ease-in-out infinite;
}}
.working-msg::before {{
    content:'';
    display:block; width:32px; height:32px; margin:0 auto 16px;
    border:2px solid {BORDER}; border-top-color:{TEAL};
    border-radius:50%;
    animation:spin .8s linear infinite;
}}
@keyframes spin {{ to {{ transform:rotate(360deg); }} }}

/* ─── Landing page ─── */
.lp-wrap {{
    text-align:center;
    padding:60px 0 44px;
    animation:fadeInUp .6s ease-out;
}}
.brand-title {{
    font-size:3.6rem; font-weight:900; line-height:1;
    letter-spacing:-.04em; color:{WHITE};
}}
.brand-accent {{ color:{TEAL}; }}
.brand-pill {{
    display:inline-block;
    background:rgba(0,200,150,.12);
    color:{TEAL}; border:1px solid rgba(0,200,150,.3);
    font-size:.72rem; font-weight:700; letter-spacing:.16em;
    text-transform:uppercase; padding:5px 14px;
    border-radius:100px; margin-top:14px;
}}
.brand-desc {{
    color:{GRAY}; font-size:.95rem; line-height:1.75;
    margin-top:18px; max-width:560px; margin-left:auto; margin-right:auto;
}}

/* Upload card inner labels */
.uc-icon  {{ font-size:1.5rem; margin-bottom:8px; line-height:1; }}
.uc-title {{
    font-size:.95rem; font-weight:700; color:{WHITE};
    margin:0 0 4px;
}}
.uc-badge {{
    display:inline-block;
    background:rgba(0,200,150,.12); color:{TEAL};
    border:1px solid rgba(0,200,150,.3);
    font-size:.65rem; font-weight:700;
    letter-spacing:.1em; padding:2px 7px;
    border-radius:4px; margin-left:6px; vertical-align:middle;
}}
.uc-hint {{
    color:{GRAY}; font-size:.8rem; line-height:1.55;
    margin-bottom:12px;
}}

.or-row {{
    display:flex; align-items:center; gap:10px;
    color:{GRAY}; font-size:.72rem; letter-spacing:.12em;
    font-weight:600; margin-bottom:0; padding-bottom:0;
}}
.or-row::before, .or-row::after {{
    content:'';flex:1;height:1px;background:{BORDER};
}}

/* ─── Full-page analysis loading screen ─── */
.analysis-loading-page {{
    display:flex; flex-direction:column; align-items:center; justify-content:center;
    min-height:70vh; animation:fadeInUp .5s ease-out;
}}
.alp-spinner {{
    width:56px; height:56px;
    border:3px solid {BORDER};
    border-top-color:{TEAL};
    border-radius:50%;
    animation:spin .9s linear infinite;
    margin-bottom:28px;
}}
.alp-title {{
    font-size:1.45rem; font-weight:800; color:{WHITE};
    letter-spacing:-.02em; margin-bottom:10px;
}}
.alp-sub {{
    font-size:.9rem; color:{GRAY}; font-weight:500;
    animation:pulse 2s ease-in-out infinite;
}}

/* ─── Sequential section loading card ─── */
.section-card-loading {{
    background:{BG_CARD};
    border:1px solid {BORDER};
    border-radius:14px;
    margin-bottom:14px;
    overflow:hidden;
    animation:fadeInUp .45s ease-out;
}}
.scl-header {{
    padding:16px 22px;
    font-size:.97rem; font-weight:700; color:{WHITE};
    border-bottom:1px solid {BORDER};
}}
.scl-body {{
    padding:52px 24px;
    text-align:center;
}}
.scl-spinner {{
    width:38px; height:38px;
    border:2px solid {BORDER};
    border-top-color:{TEAL};
    border-radius:50%;
    margin:0 auto 18px;
    animation:spin .8s linear infinite;
}}
.scl-text {{
    color:{TEAL_DIM}; font-size:.88rem; font-weight:500;
    letter-spacing:.05em;
    animation:pulse 1.6s ease-in-out infinite;
}}

.kpi-period {{
    font-size:.78rem; color:{TEAL_DIM}; text-align:right;
    letter-spacing:.04em; margin-bottom:6px; opacity:.8;
}}

/* Settings expander tweak — neutral label */
.adv-label {{
    font-size:.8rem; color:{GRAY}; font-weight:500;
}}

/* ─── Multiselect ─── */
[data-testid="stMultiSelect"] > div > div {{
    background:{BG_CARD}!important;
    border-color:{BORDER}!important;
    border-radius:10px!important;
}}
[data-baseweb="tag"] {{
    background:rgba(0,200,150,.12)!important;
    border:1px solid rgba(0,200,150,.3)!important;
    border-radius:6px!important;
}}
[data-baseweb="tag"] span {{ color:{TEAL}!important; font-weight:600!important; }}
[data-baseweb="tag"] button {{ color:{TEAL}!important; }}
.section-select-label {{
    text-align:center; font-size:.78rem; font-weight:700;
    color:{TEAL_DIM}; text-transform:uppercase; letter-spacing:.08em; margin-bottom:6px;
}}

/* ─── Chat panel ─── */
.chat-header {{
    text-align:center; margin-bottom:24px;
}}
.chat-header-title {{
    font-size:1.3rem; font-weight:800; color:{WHITE}; letter-spacing:-.02em;
}}
.chat-header-sub {{
    font-size:.88rem; color:{GRAY}; margin-top:6px;
}}
[data-testid="stChatMessage"] {{
    background:{BG_CARD}!important;
    border:1px solid {BORDER}!important;
    border-radius:14px!important;
    margin-bottom:10px!important;
}}
[data-testid="stChatMessage"] p {{ color:{WHITE}!important; }}
[data-testid="stChatInputContainer"] {{
    background:{BG_CARD}!important;
    border:1px solid {BORDER}!important;
    border-radius:12px!important;
}}
[data-testid="stChatInputContainer"] textarea {{
    background:{BG_CARD}!important;
    color:{WHITE}!important;
}}
[data-testid="stChatInputContainer"] button {{
    background:{TEAL}!important;
    border-radius:8px!important;
}}
</style>
""", unsafe_allow_html=True)


# ═════════════════════════════════════════════════════════════════════════════
# HELPERS
# ═════════════════════════════════════════════════════════════════════════════

def _save_uploaded_file(uf, dest="output/uploads"):
    os.makedirs(dest, exist_ok=True)
    path = os.path.join(dest, uf.name)
    with open(path, "wb") as f:
        f.write(uf.getbuffer())
    return path


def _plotly_dark(fig, height=400, margin=None, extra=None):
    """Apply dark theme to any Plotly figure."""
    m = margin or {"t": 28, "b": 20, "l": 60, "r": 20}
    extra = dict(extra or {})
    legend = {"bgcolor": "rgba(0,0,0,0)", "font": {"color": WHITE}}
    legend.update(extra.pop("legend", {}))
    fig.update_layout(
        height        = height,
        margin        = m,
        paper_bgcolor = BG_CARD,
        plot_bgcolor  = BG_CARD,
        font          = {"color": WHITE, "family": "Inter, sans-serif"},
        legend        = legend,
        **extra,
    )
    fig.update_xaxes(gridcolor=BORDER, zerolinecolor=BORDER, tickfont={"color": GRAY})
    fig.update_yaxes(gridcolor=BORDER, zerolinecolor=BORDER, tickfont={"color": GRAY})
    return fig


# ═════════════════════════════════════════════════════════════════════════════
# LANDING PAGE
# ═════════════════════════════════════════════════════════════════════════════

def _landing():
    """
    Full-page upload UI.  Returns a dict of settings when "Run Analysis"
    is clicked, or None if the user hasn't submitted yet.
    """
    # ── Brand header ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div class="lp-wrap">
        <div class="brand-title">Finance<span class="brand-accent">Flow</span></div>
        <div><span class="brand-pill">AI &mdash; FP&amp;A Intelligence</span></div>
        <div class="brand-desc">
            Upload your budget and actuals to get AI-powered variance analysis,
            anomaly detection, and variance commentary in under 60 seconds.
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Upload cards (3 columns with bordered containers) ─────────────────────
    c1, c2, c3 = st.columns(3, gap="large")

    with c1:
        with st.container(border=True):
            st.markdown("""
            <div class="uc-icon">&#128196;</div>
            <div class="uc-title">Budget File</div>
            <div class="uc-hint">Full-year plan &nbsp;&middot;&nbsp; .xlsx or .csv<br>
            Month &nbsp;/&nbsp; Department &nbsp;/&nbsp; Line Item &nbsp;/&nbsp; Category &nbsp;/&nbsp; Amount</div>
            """, unsafe_allow_html=True)
            budget_file = st.file_uploader("budget_file", type=["xlsx","csv"],
                                           label_visibility="collapsed", key="uf_budget")
            if budget_file:
                st.success(f"{budget_file.name}")

    with c2:
        with st.container(border=True):
            st.markdown("""
            <div class="uc-icon">&#128202;</div>
            <div class="uc-title">Actuals File</div>
            <div class="uc-hint">Closed months only &nbsp;&middot;&nbsp; .xlsx or .csv<br>
            Same five-column format as the budget file</div>
            """, unsafe_allow_html=True)
            actuals_file = st.file_uploader("actuals_file", type=["xlsx","csv"],
                                            label_visibility="collapsed", key="uf_actuals")
            if actuals_file:
                st.success(f"{actuals_file.name}")

    with c3:
        with st.container(border=True):
            st.markdown(f"""
            <div class="uc-icon">&#128172;</div>
            <div class="uc-title">Drivers File<span class="uc-badge">Optional</span></div>
            <div class="uc-hint">Budget owner explanations &nbsp;&middot;&nbsp; .csv<br>
            Month &nbsp;/&nbsp; Department &nbsp;/&nbsp; Line Item &nbsp;/&nbsp; Driver Note</div>
            """, unsafe_allow_html=True)
            drivers_file = st.file_uploader("drivers_file", type=["csv"],
                                            label_visibility="collapsed", key="uf_drivers")
            if drivers_file:
                st.success(f"{drivers_file.name}")

    all_required = bool(budget_file and actuals_file)

    # ── OR divider + demo checkbox stacked, zero gap between them ────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, mid_col, _ = st.columns([2, 3, 2])
    with mid_col:
        st.markdown('<div class="or-row">or</div>', unsafe_allow_html=True)
        use_demo = st.checkbox(
            "Use demo data — sample SaaS company (FY2026)",
            value=not all_required,
            key="use_demo_cb",
        )

    # ── Analysis section selector ─────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, sel_col, _ = st.columns([1, 5, 1])
    with sel_col:
        st.markdown('<div class="section-select-label">Select analyses to include</div>',
                    unsafe_allow_html=True)
        all_section_names = [
            "Operating Income Bridge",
            "Anomaly Detection",
            "Year-End Forecast Projection",
            "Variance Heatmap — Line x Month",
            "Budget vs Actual — Trend Explorer",
            "YTD Variance Detail",
        ]
        selected_sections = st.multiselect(
            "sections", options=all_section_names, default=all_section_names,
            label_visibility="collapsed", key="section_select",
        )

    # ── Run button ────────────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    _, btn_col, _ = st.columns([2, 3, 2])
    with btn_col:
        run_clicked = st.button("Run Analysis", type="primary",
                                key="run_btn", use_container_width=True)

    # ── Advanced settings ─────────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    mat_dollars = int(config.MATERIALITY_THRESHOLD_DOLLARS)
    mat_pct     = float(config.MATERIALITY_THRESHOLD_PERCENT)
    with st.expander("Advanced — materiality thresholds", expanded=False):
        st.markdown('<p class="adv-label">A variance is flagged as material when it clears '
                    '<strong>either</strong> threshold.</p>', unsafe_allow_html=True)
        tc1, tc2 = st.columns(2)
        with tc1:
            mat_dollars = st.number_input(
                "Dollar threshold",
                min_value=0, max_value=1_000_000,
                value=int(config.MATERIALITY_THRESHOLD_DOLLARS),
                step=5_000, key="mat_d",
            )
        with tc2:
            mat_pct = st.number_input(
                "Percent of budget (%)",
                min_value=0.0, max_value=100.0,
                value=float(config.MATERIALITY_THRESHOLD_PERCENT),
                step=0.5, key="mat_p",
            )

    if not run_clicked:
        return None

    # ── Resolve file paths ────────────────────────────────────────────────────
    if all_required and not use_demo:
        bp = _save_uploaded_file(budget_file)
        ap = _save_uploaded_file(actuals_file)
        dp = _save_uploaded_file(drivers_file) if drivers_file else None
        chash = hash(budget_file.getvalue() + actuals_file.getvalue())
    elif use_demo:
        bp, ap, dp = config.BUDGET_PATH, config.ACTUALS_PATH, config.DRIVERS_PATH
        chash = "demo"
    else:
        st.error("Upload a Budget and Actuals file, or check 'Use demo data' to continue.")
        return None

    if not selected_sections:
        st.error("Select at least one analysis section to continue.")
        return None

    return dict(budget_path=bp, actuals_path=ap, drivers_path=dp,
                mat_dollars=mat_dollars, mat_pct=mat_pct,
                content_hash=chash, using_demo=use_demo,
                selected_sections=selected_sections)


# ═════════════════════════════════════════════════════════════════════════════
# PIPELINE — STEP BY STEP (with live status updates)
# ═════════════════════════════════════════════════════════════════════════════

def _run_analysis(settings: dict):
    """
    Run each pipeline step individually so the st.status() box can show
    real progress.  Stores results in st.session_state.
    """
    # Inject a full-viewport Three.js overlay into the parent window from iframe
    components.html("""<!DOCTYPE html><html><body style="margin:0">
<script>
(function(){
  var p = window.parent.document;
  if (p.getElementById('ff-overlay')) return;

  // Full-screen overlay
  var ov = p.createElement('div');
  ov.id  = 'ff-overlay';
  ov.style.cssText = [
    'position:fixed','inset:0','z-index:9999',
    'background:#0B1916',
    'display:flex','flex-direction:column',
    'align-items:center','justify-content:center',
    'font-family:Inter,system-ui,sans-serif','overflow:hidden'
  ].join(';');

  // Canvas (behind text)
  var cv = p.createElement('canvas');
  cv.id  = 'ff-cv';
  cv.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;';
  ov.appendChild(cv);

  // Text layer
  var tx = p.createElement('div');
  tx.style.cssText = 'position:relative;z-index:2;text-align:center;';
  tx.innerHTML =
    '<div style="font-size:2.5rem;font-weight:900;color:#fff;letter-spacing:-.04em;margin-bottom:14px">Running Analysis</div>' +
    '<div id="ff-sub" style="font-size:.95rem;color:#8FADA6;font-weight:500">Analysing your financial data…</div>' +
    '<style>@keyframes ff-pulse{0%,100%{opacity:.45}50%{opacity:1}}#ff-sub{animation:ff-pulse 2s ease-in-out infinite}</style>';
  ov.appendChild(tx);
  p.body.appendChild(ov);

  // Load Three.js into parent window
  var s = p.createElement('script');
  s.src = 'https://cdnjs.cloudflare.com/ajax/libs/three.js/r128/three.min.js';
  s.onload = function(){
    var T  = window.parent.THREE;
    var W  = window.parent.innerWidth;
    var H  = window.parent.innerHeight;

    var scene  = new T.Scene();
    var cam    = new T.PerspectiveCamera(70, W/H, 0.1, 1000);
    cam.position.z = 10;

    var rdr = new T.WebGLRenderer({ canvas: p.getElementById('ff-cv'), antialias: true });
    rdr.setPixelRatio(window.parent.devicePixelRatio || 1);
    rdr.setSize(W, H);
    rdr.setClearColor(0x0B1916, 1);

    // Particle field
    var N   = 500;
    var pos = new Float32Array(N * 3);
    var vel = [];
    for (var i = 0; i < N; i++) {
      pos[i*3]   = (Math.random() - .5) * 30;
      pos[i*3+1] = (Math.random() - .5) * 30;
      pos[i*3+2] = (Math.random() - .5) * 12;
      vel.push([(Math.random()-.5)*.024, (Math.random()-.5)*.024]);
    }
    var geo = new T.BufferGeometry();
    geo.setAttribute('position', new T.BufferAttribute(pos, 3));
    var mat = new T.PointsMaterial({ color: 0x00C896, size: .07, transparent: true, opacity: .8 });
    var pts = new T.Points(geo, mat);
    scene.add(pts);

    // Faint data-grid behind particles
    var grid = new T.GridHelper(40, 24, 0x1E3D30, 0x1E3D30);
    grid.rotation.x = Math.PI / 2;
    grid.position.z = -6;
    grid.material.transparent = true;
    grid.material.opacity = .12;
    scene.add(grid);

    var aid;
    function tick(){
      aid = requestAnimationFrame(tick);
      var a = pts.geometry.attributes.position.array;
      for (var i = 0; i < N; i++){
        a[i*3]   += vel[i][0];
        a[i*3+1] += vel[i][1];
        if (Math.abs(a[i*3])   > 15) vel[i][0] *= -1;
        if (Math.abs(a[i*3+1]) > 15) vel[i][1] *= -1;
      }
      pts.geometry.attributes.position.needsUpdate = true;
      pts.rotation.z  += .0005;
      grid.rotation.z += .0002;
      rdr.render(scene, cam);
    }
    tick();

    window.parent.__ffStop = function(){
      cancelAnimationFrame(aid);
      rdr.dispose();
    };
  };
  p.head.appendChild(s);
})();
</script>
</body></html>""", height=1)

    try:
        data        = load_data(settings["budget_path"],
                                settings["actuals_path"],
                                settings["drivers_path"])
        results     = run_variance_engine(data)
        commentary  = generate_commentary(results, data)
        report_path = build_report(results, commentary)

    except (FileNotFoundError, ValueError) as e:
        st.error(f"**Error:** {e}")
        if st.button("Go back"):
            del st.session_state["settings"]
            st.rerun()
        return

    st.session_state["pipeline_output"] = dict(
        data=data, results=results, commentary=commentary, report_path=report_path
    )
    st.session_state["dashboard_animated"] = False
    st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# KPI CARDS
# ═════════════════════════════════════════════════════════════════════════════

def _kpi_cards(output):
    pl  = output["results"]["pl_summary"]
    mon = output["results"]["monthly"]

    def pr(name):
        r = pl[pl["Line"] == name]
        return r.iloc[0] if not r.empty else None

    rev  = pr("Revenue")
    opex = pr("Opex")
    oi   = pr("Operating Income")
    mat  = int(mon["Material"].sum())
    anom = len(output["results"]["anomalies"])

    months = sorted(output["data"]["closed_months"])
    period = f"{months[0]} → {months[-1]}"
    st.markdown(f'<div class="kpi-period">YTD Period: {period}</div>',
                unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4, gap="medium")
    with c1:
        if rev is not None:
            st.metric("YTD Revenue",
                      f"${rev['Actual']:,.0f}",
                      f"${rev['Variance $']:+,.0f} vs budget",
                      delta_color="normal")
    with c2:
        if opex is not None:
            st.metric("YTD Operating Expenses",
                      f"${opex['Actual']:,.0f}",
                      f"${opex['Variance $']:+,.0f} vs budget",
                      delta_color="inverse")
    with c3:
        if oi is not None:
            st.metric("YTD Operating Income",
                      f"${oi['Actual']:,.0f}",
                      f"${oi['Variance $']:+,.0f} vs budget",
                      delta_color="normal")
    with c4:
        st.metric("Material Variances",
                  str(mat),
                  f"{anom} anomalies detected",
                  delta_color="off")


# ═════════════════════════════════════════════════════════════════════════════
# WATERFALL
# ═════════════════════════════════════════════════════════════════════════════

def _waterfall(output):
    pl = output["results"]["pl_summary"]
    def v(name, col):
        r = pl[pl["Line"] == name]
        return r.iloc[0][col] if not r.empty else 0

    b_oi  = v("Operating Income", "Budget")
    r_imp = v("Revenue",          "Net Impact $")
    c_imp = v("COGS",             "Net Impact $")
    o_imp = v("Opex",             "Net Impact $")
    a_oi  = v("Operating Income", "Actual")

    fig = go.Figure(go.Waterfall(
        orientation  = "v",
        measure      = ["absolute","relative","relative","relative","total"],
        x            = ["Budget OI","Revenue","COGS","Opex","Actual OI"],
        y            = [b_oi, r_imp, c_imp, o_imp, a_oi],
        text         = [f"${x:,.0f}" for x in [b_oi,r_imp,c_imp,o_imp,a_oi]],
        textposition = "outside",
        textfont     = {"color": WHITE, "size": 12},
        decreasing   = {"marker": {"color": RED,   "line": {"color": RED,   "width":1}}},
        increasing   = {"marker": {"color": GREEN, "line": {"color": GREEN, "width":1}}},
        totals       = {"marker": {"color": TEAL,  "line": {"color": TEAL,  "width":1}}},
        connector    = {"line": {"color": BORDER, "dash":"dot", "width":1}},
    ))
    fig.add_hline(y=0, line_color=GRAY, line_width=1, opacity=0.5)
    fig = _plotly_dark(fig, height=400,
                       extra={"yaxis": {"tickformat":"$,.0f"}})
    st.plotly_chart(fig, use_container_width=True)


# ═════════════════════════════════════════════════════════════════════════════
# ANOMALY ALERTS
# ═════════════════════════════════════════════════════════════════════════════

def _anomalies(output):
    anom = output["results"]["anomalies"]
    if anom.empty:
        st.info("No anomalies detected in this dataset.")
        return

    types = {
        "Missing Driver": {
            "label": "Missing Driver Notes — chase list before distributing the report",
            "fn": st.error,
        },
        "Spike": {
            "label": "Variance Spikes — single-month variance unusually large vs own history",
            "fn": st.warning,
        },
        "Consecutive Deterioration": {
            "label": "Consecutive Deterioration — net OI impact worsening 3+ months in a row",
            "fn": st.warning,
        },
    }
    for atype, cfg in types.items():
        subset = anom[anom["Type"] == atype]
        if subset.empty:
            continue
        with st.expander(f"{cfg['label']}  ({len(subset)})",
                         expanded=(atype == "Missing Driver")):
            for _, row in subset.iterrows():
                cfg["fn"](row["Description"])


# ═════════════════════════════════════════════════════════════════════════════
# HEATMAP
# ═════════════════════════════════════════════════════════════════════════════

def _heatmap(output):
    mon = output["results"]["monthly"]
    pivot = mon.pivot_table(index="Line Item", columns="Month",
                            values="Net Impact $", aggfunc="sum", fill_value=0)
    texts = [[f"${v:+,.0f}" for v in row] for row in pivot.values]

    fig = go.Figure(go.Heatmap(
        z             = pivot.values,
        x             = list(pivot.columns),
        y             = list(pivot.index),
        colorscale    = [[0.0, RED],[0.45,"#5C2020"],[0.5, BG_MID],
                         [0.55,"#1A4A38"],[1.0, GREEN]],
        zmid          = 0,
        text          = texts,
        texttemplate  = "%{text}",
        textfont      = {"size": 11, "color": WHITE},
        hovertemplate = "<b>%{y}</b><br>%{x}<br>Net Impact: %{text}<extra></extra>",
        showscale     = True,
        colorbar      = {"title":{"text":"Net Impact","font":{"color":WHITE}},
                         "tickformat":"$,.0f","tickfont":{"color":WHITE}},
    ))
    fig = _plotly_dark(fig, height=430,
                       margin={"t":20,"b":20,"l":190,"r":20},
                       extra={"xaxis":{"side":"top"},
                              "yaxis":{"autorange":"reversed"}})
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Green = favorable net impact on OI.  Red = unfavorable.  "
               "Revenue: above budget = green.  Costs: below budget = green.")


# ═════════════════════════════════════════════════════════════════════════════
# TREND EXPLORER
# ═════════════════════════════════════════════════════════════════════════════

def _trend(output):
    mon   = output["results"]["monthly"]
    items = sorted(mon["Line Item"].unique())

    col1, col2 = st.columns([3, 2])
    with col1:
        sel = st.selectbox("Line item", items,
                           index=items.index("Subscription Revenue")
                           if "Subscription Revenue" in items else 0,
                           key="trend_item")
    with col2:
        depts = mon[mon["Line Item"] == sel]["Department"].unique()
        sel_dept = st.selectbox("Department", ["All"]+sorted(depts), key="trend_dept")

    filt = mon[mon["Line Item"] == sel]
    if sel_dept != "All":
        filt = filt[filt["Department"] == sel_dept]
    if filt.empty:
        st.warning("No data for this selection.")
        return

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=filt["Month"], y=filt["Amount_budget"],
        name="Budget", mode="lines+markers",
        line={"dash":"dash","color":TEAL_DIM,"width":2}, marker={"size":7},
    ))
    fig.add_trace(go.Scatter(
        x=filt["Month"], y=filt["Amount_actual"],
        name="Actual", mode="lines+markers",
        line={"color":TEAL,"width":2.5}, marker={"size":9,"symbol":"circle"},
    ))
    # Gap shading
    fig.add_trace(go.Scatter(
        x    = list(filt["Month"]) + list(filt["Month"])[::-1],
        y    = list(filt["Amount_actual"]) + list(filt["Amount_budget"])[::-1],
        fill = "toself", fillcolor="rgba(224,82,82,0.07)",
        line = {"color":"rgba(0,0,0,0)"}, showlegend=False, hoverinfo="skip",
    ))
    # Material month markers
    for m in filt[filt["Material"]]["Month"]:
        fig.add_vline(x=m, line_dash="dot", line_color=RED,
                      line_width=1.2, opacity=0.7)

    cat = filt["Category"].iloc[0]
    fig = _plotly_dark(fig, height=370,
                       extra={
                           "title": {"text": f"{sel}  ·  {cat}", "font":{"size":13,"color":WHITE}},
                           "yaxis": {"tickformat":"$,.0f"},
                           "legend": {"orientation":"h","y":-0.15},
                       })
    st.plotly_chart(fig, use_container_width=True)

    # Mini table
    mini = filt[["Month","Department","Amount_budget","Amount_actual",
                 "Variance $","Variance %","F/U","Material"]].copy()
    mini["Amount_budget"] = mini["Amount_budget"].map("${:,.0f}".format)
    mini["Amount_actual"] = mini["Amount_actual"].map("${:,.0f}".format)
    mini["Variance $"]    = mini["Variance $"].map("${:+,.0f}".format)
    mini["Variance %"]    = mini["Variance %"].map("{:+.1f}%".format)
    mini["Material"]      = mini["Material"].map({True:"Yes", False:""})
    st.dataframe(mini, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# YEAR-END FORECAST PROJECTION
# ═════════════════════════════════════════════════════════════════════════════

def _forecast(output):
    data          = output["data"]
    budget        = data["budget"]
    ytd           = output["results"]["ytd"].copy()
    closed        = data["closed_months"]
    total_months  = budget["Month"].nunique()
    remaining     = total_months - len(closed)

    # ── Full-year budget per line item ────────────────────────────────────────
    fy_bud = (
        budget.groupby(["Line Item", "Department", "Category"])["Amount"]
        .sum().reset_index()
        .rename(columns={"Amount": "FY_Budget"})
    )

    # ── Merge with YTD actuals ────────────────────────────────────────────────
    fc = fy_bud.merge(
        ytd[["Line Item", "Department", "YTD_Actual", "YTD_Budget"]],
        on=["Line Item", "Department"], how="left",
    ).fillna(0)

    fc["Remaining_Budget"] = fc["FY_Budget"] - fc["YTD_Budget"]
    fc["FY_Forecast"]      = fc["YTD_Actual"] + fc["Remaining_Budget"]
    fc["vs_Bud"]           = fc["FY_Forecast"] - fc["FY_Budget"]
    fc["vs_Bud_pct"]       = (
        fc["vs_Bud"] / fc["FY_Budget"].replace(0, float("nan")) * 100
    )

    # ── P&L rollup ────────────────────────────────────────────────────────────
    def s(col, cat):
        return fc[fc["Category"] == cat][col].sum()

    rev_bud  = s("FY_Budget",   "Revenue");  rev_fc  = s("FY_Forecast", "Revenue")
    cogs_bud = s("FY_Budget",   "COGS");     cogs_fc = s("FY_Forecast", "COGS")
    gp_bud   = rev_bud  - cogs_bud;         gp_fc   = rev_fc  - cogs_fc
    opex_bud = s("FY_Budget",   "Opex");     opex_fc = s("FY_Forecast", "Opex")
    oi_bud   = gp_bud   - opex_bud;         oi_fc   = gp_fc   - opex_fc

    # ── Info bar ──────────────────────────────────────────────────────────────
    st.markdown(
        f'<div style="text-align:center;color:{GRAY};font-size:.85rem;margin-bottom:22px;">'
        f'Based on <strong style="color:{TEAL}">{len(closed)} of {total_months} months closed'
        f'</strong> &nbsp;·&nbsp; '
        f'<strong style="color:{WHITE}">{remaining} months</strong> remaining at budget'
        f'</div>',
        unsafe_allow_html=True,
    )

    # ── Forecast KPI cards ────────────────────────────────────────────────────
    def fc_card(label, bud, fore, fav_pos=True):
        gap   = fore - bud
        pct   = (gap / bud * 100) if bud else 0
        fav   = (gap > 0) == fav_pos
        color = TEAL if fav else RED
        tag   = "Favorable" if fav else "Unfavorable"
        return label, bud, fore, gap, pct, color, tag

    card_defs = [
        fc_card("FY Revenue",          rev_bud,  rev_fc,  fav_pos=True),
        fc_card("FY Gross Profit",     gp_bud,   gp_fc,   fav_pos=True),
        fc_card("FY Opex",             opex_bud, opex_fc, fav_pos=False),
        fc_card("FY Operating Income", oi_bud,   oi_fc,   fav_pos=True),
    ]

    cols = st.columns(4, gap="medium")
    for col, (label, bud, fore, gap, pct, color, tag) in zip(cols, card_defs):
        with col:
            st.markdown(f"""
            <div style="background:{BG_MID};border:1px solid {BORDER};border-radius:14px;
                        padding:18px 20px;">
                <div style="font-size:.68rem;font-weight:700;color:{TEAL_DIM};
                            text-transform:uppercase;letter-spacing:.08em;margin-bottom:10px;">
                    {label}
                </div>
                <div style="font-size:1.3rem;font-weight:800;color:{WHITE};">
                    ${fore:,.0f}
                </div>
                <div style="font-size:.8rem;margin-top:6px;color:{color};font-weight:600;">
                    {'+' if gap >= 0 else ''}{gap:,.0f} ({pct:+.1f}%) vs budget
                </div>
                <div style="font-size:.72rem;color:{GRAY};margin-top:4px;">
                    {tag} &nbsp;·&nbsp; Budget: ${bud:,.0f}
                </div>
            </div>""", unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Grouped bar chart: Budget vs Forecast ─────────────────────────────────
    pl_names     = ["Revenue", "Gross Profit", "Opex", "Op. Income"]
    pl_budgets   = [rev_bud,  gp_bud,  opex_bud,  oi_bud]
    pl_forecasts = [rev_fc,   gp_fc,   opex_fc,   oi_fc]
    fav_flags    = [rev_fc >= rev_bud, gp_fc >= gp_bud,
                    opex_fc <= opex_bud, oi_fc >= oi_bud]
    bar_colors   = [TEAL if f else RED for f in fav_flags]

    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="FY Budget", x=pl_names, y=pl_budgets,
        marker_color=BG_MID, marker_line_color=TEAL_DIM, marker_line_width=1.5,
        text=[f"${v:,.0f}" for v in pl_budgets],
        textposition="outside", textfont={"color": GRAY, "size": 11},
    ))
    fig.add_trace(go.Bar(
        name="FY Forecast", x=pl_names, y=pl_forecasts,
        marker_color=bar_colors, marker_opacity=0.88,
        text=[f"${v:,.0f}" for v in pl_forecasts],
        textposition="outside", textfont={"color": WHITE, "size": 11},
    ))
    fig = _plotly_dark(fig, height=390, extra={
        "barmode":      "group",
        "bargap":       0.28,
        "bargroupgap":  0.08,
        "yaxis":        {"tickformat": "$,.0f"},
        "title":        {"text": "Full-Year P&L: Budget vs Forecast",
                         "font": {"size": 13, "color": WHITE}},
    })
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Green = forecast tracking ahead of budget.  "
               "Red = forecast tracking behind budget.  "
               "Opex: green means spending below budget (favorable).")

    # ── Line item detail table ─────────────────────────────────────────────────
    with st.expander("Line Item Detail", expanded=False):
        disp = fc[["Department", "Line Item", "Category",
                    "FY_Budget", "YTD_Actual", "Remaining_Budget",
                    "FY_Forecast", "vs_Bud", "vs_Bud_pct"]].copy()
        disp.columns = ["Department", "Line Item", "Category",
                        "FY Budget", "YTD Actual", "Remaining Budget",
                        "FY Forecast", "vs Budget $", "vs Budget %"]
        for c in ["FY Budget", "YTD Actual", "Remaining Budget", "FY Forecast"]:
            disp[c] = disp[c].map("${:,.0f}".format)
        disp["vs Budget $"] = disp["vs Budget $"].map("${:+,.0f}".format)
        disp["vs Budget %"] = disp["vs Budget %"].map("{:+.1f}%".format)
        st.dataframe(disp, use_container_width=True, hide_index=True)


# ═════════════════════════════════════════════════════════════════════════════
# YTD TABLE
# ═════════════════════════════════════════════════════════════════════════════

def _ytd_table(output):
    ytd   = output["results"]["ytd"].copy()
    comms = output["commentary"]["line_commentary"]

    def get_c(dept, line):
        m = {k:v for k,v in comms.items() if k[1]==dept and k[2]==line}
        return m[max(m, key=lambda k:k[0])] if m else ""

    ytd["Commentary"] = ytd.apply(lambda r: get_c(r["Department"], r["Line Item"]), axis=1)

    f1, f2, f3 = st.columns(3)
    with f1:
        df = st.selectbox("Department", ["All"]+sorted(ytd["Department"].unique()), key="yt_d")
    with f2:
        cf = st.selectbox("Category", ["All"]+sorted(ytd["Category"].unique()), key="yt_c")
    with f3:
        mf = st.selectbox("Show", ["All","Material only","Non-material only"], key="yt_m")

    t = ytd.copy()
    if df != "All": t = t[t["Department"]==df]
    if cf != "All": t = t[t["Category"]==cf]
    if mf == "Material only":     t = t[t["YTD_Material"]]
    elif mf == "Non-material only": t = t[~t["YTD_Material"]]

    disp = t[["Department","Line Item","Category",
              "YTD_Budget","YTD_Actual","YTD_Var","YTD_Var_Pct",
              "YTD_FU","YTD_Material","Commentary"]].copy()
    disp.columns = ["Department","Line Item","Category",
                    "YTD Budget","YTD Actual","Variance $","Variance %",
                    "F/U","Material","Commentary"]
    disp["YTD Budget"] = disp["YTD Budget"].map("${:,.0f}".format)
    disp["YTD Actual"] = disp["YTD Actual"].map("${:,.0f}".format)
    disp["Variance $"] = disp["Variance $"].map("${:+,.0f}".format)
    disp["Variance %"] = disp["Variance %"].map("{:+.1f}%".format)
    disp["Material"]   = disp["Material"].map({True:"Yes", False:""})

    def row_color(row):
        if row["Material"] == "Yes":
            return (["background-color:#0F2E1A"]*len(row) if row["F/U"]=="Favorable"
                    else ["background-color:#2E0F0F"]*len(row))
        return [""]*len(row)

    st.dataframe(disp.style.apply(row_color, axis=1),
                 use_container_width=True, hide_index=True,
                 column_config={"Commentary": st.column_config.TextColumn(width="large")})
    st.caption(f"Showing {len(disp)} of {len(ytd)} line items.  "
               "Dark green = material favorable.  Dark red = material unfavorable.")


# ═════════════════════════════════════════════════════════════════════════════
# CHAT — Claude Q&A on the loaded variance data
# ═════════════════════════════════════════════════════════════════════════════

def _build_context(output: dict) -> str:
    """Summarise all analysis results into a text block for the system prompt."""
    results = output["results"]
    data    = output["data"]
    months  = data["closed_months"]
    period  = f"{months[0]} to {months[-1]}"

    # P&L summary
    pl_text = "\n".join(
        f"  {r['Line']}: Budget ${r['Budget']:,.0f} | Actual ${r['Actual']:,.0f} | "
        f"Variance ${r['Variance $']:+,.0f} ({r['Variance %']:+.1f}%) [{r['F/U']}]"
        for _, r in results["pl_summary"].iterrows()
    )

    # Top 10 material monthly variances
    mon  = results["monthly"]
    mmat = mon[mon["Material"]].sort_values("Net Impact $").head(10)
    mat_text = "\n".join(
        f"  {r['Month']} | {r['Department']} | {r['Line Item']}: "
        f"${r['Variance $']:+,.0f} ({r['Variance %']:+.1f}%) [{r['F/U']}]"
        for _, r in mmat.iterrows()
    ) or "  None."

    # Anomalies
    anom = results["anomalies"]
    anom_text = "\n".join(
        f"  [{r['Type']}] {r['Description']}" for _, r in anom.iterrows()
    ) if not anom.empty else "  None detected."

    # Top 5 YTD variances by net impact
    ytd = results["ytd"].sort_values("YTD_NetImp").head(5)
    ytd_text = "\n".join(
        f"  {r['Line Item']} ({r['Department']}): YTD ${r['YTD_Var']:+,.0f} "
        f"({r['YTD_Var_Pct']:+.1f}%) [{r['YTD_FU']}]"
        for _, r in ytd.iterrows()
    )

    # Driver notes
    drivers = data["drivers"]
    drv_text = "\n".join(
        f"  {r['Month']} | {r['Department']} | {r['Line Item']}: {r['Driver Note']}"
        for _, r in drivers.iterrows()
    ) if not drivers.empty else "  No driver notes on file."

    return f"""You are an expert FP&A analyst assistant embedded in FinanceFlow-AI.
The user is reviewing variance analysis for the period {period}.

P&L SUMMARY:
{pl_text}

TOP MATERIAL MONTHLY VARIANCES:
{mat_text}

ANOMALIES DETECTED:
{anom_text}

TOP 5 YTD VARIANCES BY IMPACT ON OPERATING INCOME:
{ytd_text}

DRIVER NOTES FROM BUDGET OWNERS:
{drv_text}

Answer questions about this specific data concisely and precisely. Always reference \
specific numbers from the data above. If asked about something not in the data, say so \
clearly. Never invent figures or causes not present above. Write for a finance professional."""


def _get_chat_response(output: dict) -> str:
    """Send the current chat history + context to Claude and return the reply."""
    try:
        import anthropic
    except ImportError:
        return "Install the `anthropic` package to enable chat."

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        return "Add ANTHROPIC_API_KEY to your .env file to enable chat."

    history = st.session_state.get("chat_history", [])
    messages = [{"role": m["role"], "content": m["content"]} for m in history]

    try:
        client   = anthropic.Anthropic(api_key=api_key)
        response = client.messages.create(
            model      = config.CLAUDE_MODEL,
            max_tokens = 600,
            system     = _build_context(output),
            messages   = messages,
        )
        return response.content[0].text.strip()
    except anthropic.AuthenticationError:
        return "API key is invalid or expired. Check ANTHROPIC_API_KEY in your .env file."
    except anthropic.APIConnectionError:
        return "Could not reach Anthropic — check your internet connection and try again."
    except anthropic.RateLimitError:
        return "Rate limit hit. Wait a moment and try again."
    except Exception as e:
        return f"Unexpected error: {e}"


def _chat_panel(output: dict):
    """Render the chat UI at the bottom of the dashboard."""
    st.markdown(
        f'<hr style="border-color:{BORDER};opacity:.5;margin:32px 0 28px">',
        unsafe_allow_html=True,
    )
    st.markdown("""
    <div class="chat-header">
        <div class="chat-header-title">Chat with your Data</div>
        <div class="chat-header-sub">
            Ask anything — "What's driving the May shortfall?" &nbsp;·&nbsp;
            "Which department has the worst trend?" &nbsp;·&nbsp;
            "Summarise the top 3 risks"
        </div>
    </div>
    """, unsafe_allow_html=True)

    if "chat_history" not in st.session_state:
        st.session_state["chat_history"] = []

    # Render existing conversation
    for msg in st.session_state["chat_history"]:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # Inline input form (avoids Streamlit's sticky-bottom chat_input)
    with st.form("chat_form", clear_on_submit=True):
        ci, cb = st.columns([6, 1])
        with ci:
            question = st.text_input(
                "question", placeholder="Ask about your variances…",
                label_visibility="collapsed",
            )
        with cb:
            send = st.form_submit_button("Send", use_container_width=True)

    if send and question:
        st.session_state["chat_history"].append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Analysing…"):
                reply = _get_chat_response(output)
            st.markdown(reply)
        st.session_state["chat_history"].append({"role": "assistant", "content": reply})
        st.rerun()


# ═════════════════════════════════════════════════════════════════════════════
# DASHBOARD — progressive section reveal
# ═════════════════════════════════════════════════════════════════════════════

SECTIONS = [
    ("Operating Income Bridge",          _waterfall),
    ("Anomaly Detection",                _anomalies),
    ("Year-End Forecast Projection",     _forecast),
    ("Variance Heatmap — Line x Month",  _heatmap),
    ("Budget vs Actual — Trend Explorer", _trend),
    ("YTD Variance Detail",              _ytd_table),
]

def _anchor_id(title: str) -> str:
    return "ff-sec-" + "".join(c if c.isalnum() else "-" for c in title)


def _dashboard(output):
    # ── Remove Three.js loading overlay ──────────────────────────────────────
    components.html("""<script>
    (function(){
      var d = window.parent.document;

      // Remove Three.js loading overlay
      if (window.parent.__ffStop) window.parent.__ffStop();
      var ov = d.getElementById('ff-overlay');
      if (ov) ov.remove();

      // Streamlit sets stMain margin-top via JS (not CSS) — we can't override it with CSS.
      // Instead, apply an equal negative margin-top to .block-container to cancel it out.
      // React does not manage block-container's inline style, so this persists.
      function fixGap(){
        var main = d.querySelector('section[data-testid="stMain"]');
        var bc   = d.querySelector('[data-testid="stMainBlockContainer"]')
                || d.querySelector('.main .block-container');
        if(!main || !bc) return;
        var mt = parseFloat(window.parent.getComputedStyle(main).marginTop) || 0;
        if(mt > 0) bc.style.setProperty('margin-top', '-' + mt + 'px', 'important');
        bc.style.setProperty('padding-top', '0px', 'important');
      }
      fixGap();
      setTimeout(fixGap, 300);

      // Attach Home click — poll until the span exists, attach once, then stop
      var homeTimer = setInterval(function(){
        var h = d.getElementById('ff-nav-home');
        if(!h) return;
        clearInterval(homeTimer);
        h.onclick = function(){ window.parent.location.reload(); };
      }, 100);
    })();
    </script>""", height=0)

    # ── Determine active sections ─────────────────────────────────────────────
    all_names         = [t for t, _ in SECTIONS]
    current_selected  = list(st.session_state.get("settings", {}).get(
        "selected_sections", all_names
    ))

    active_sections = [(t, fn) for t, fn in SECTIONS if t in set(current_selected)]
    active_titles   = [t for t, _ in active_sections]

    # ── Fixed two-tier header (visual only — onclick attached via components.html) ─
    nav_links_html = ""
    for i, _title in enumerate(active_titles):
        nav_links_html += (
            f'<span id="ff-nav-{i}" '
            'style="color:#8FADA6;font-size:.73rem;font-weight:600;cursor:pointer;'
            'padding:5px 10px;border-radius:6px;white-space:nowrap;flex-shrink:0;transition:color .15s,background .15s;">'
            f"{_title}</span>"
        )
    st.markdown(f"""
<style>
#ff-nav-home:hover{{background:rgba(0,200,150,.12)!important;}}
#ff-navbar span[id^="ff-nav-"]:not(#ff-nav-home):hover{{color:#00C896!important;background:rgba(0,200,150,.09)!important;}}
</style>
<div id="ff-topbar" style="position:fixed;top:0;left:0;right:0;z-index:10001;height:88px;
  background:#0B1916;border-bottom:1px solid #1E3D30;
  display:flex;align-items:center;justify-content:center;
  font-family:Inter,system-ui,sans-serif;">
  <div style="text-align:center;">
    <div style="font-size:2.6rem;font-weight:900;color:#fff;letter-spacing:-.04em;line-height:1;">
      Finance<span style="color:#00C896">Flow</span>
    </div>
    <div style="font-size:.68rem;font-weight:700;color:#7EC8B5;letter-spacing:.18em;
      text-transform:uppercase;margin-top:5px;">AI &mdash; FP&amp;A Intelligence</div>
  </div>
</div>
<div id="ff-navbar" style="position:fixed;top:94px;left:0;right:0;z-index:10000;height:46px;
  background:rgba(19,40,32,0.98);border-bottom:1px solid #1E3D30;
  display:flex;align-items:center;padding:0 20px;gap:4px;overflow-x:auto;
  font-family:Inter,system-ui,sans-serif;backdrop-filter:blur(10px);">
  <span id="ff-nav-home"
    style="color:#00C896;font-size:.78rem;font-weight:700;cursor:pointer;padding:5px 12px;
      border-radius:6px;white-space:nowrap;border:1px solid rgba(0,200,150,.35);
      margin-right:12px;flex-shrink:0;transition:background .15s;">&#8592; Home
  </span>
  <span style="color:#1E3D30;margin-right:8px;flex-shrink:0;">|</span>
  {nav_links_html}
</div>
""", unsafe_allow_html=True)

    # ── Spacer — height set dynamically by JS to account for stMain margin ──
    st.markdown('<div id="ff-spacer" style="height:148px"></div>', unsafe_allow_html=True)

    # ── KPI cards ─────────────────────────────────────────────────────────────
    _kpi_cards(output)
    st.markdown("<br>", unsafe_allow_html=True)

    first = not st.session_state.get("dashboard_animated", False)

    if first:
        for title, fn in active_sections:
            st.markdown(f'<div id="{_anchor_id(title)}" style="scroll-margin-top:130px"></div>', unsafe_allow_html=True)
            ph = st.empty()
            ph.markdown(f"""
            <div class="section-card-loading">
                <div class="scl-header">{title}</div>
                <div class="scl-body">
                    <div class="scl-spinner"></div>
                    <div class="scl-text">Analysing {title}&hellip;</div>
                </div>
            </div>""", unsafe_allow_html=True)
            time.sleep(2.0)
            ph.empty()
            with ph.container():
                with st.expander(title, expanded=True):
                    fn(output)
            components.html(
                "<script>var el=window.parent.document.querySelector('section[data-testid=\"stMain\"]')"
                "||window.parent.document.querySelector('.main')||window.parent.document.body;"
                "el.scrollTo({top:el.scrollHeight,behavior:'smooth'});</script>",
                height=0,
            )
        st.session_state["dashboard_animated"] = True

    else:
        for title, fn in active_sections:
            st.markdown(f'<div id="{_anchor_id(title)}" style="scroll-margin-top:130px"></div>', unsafe_allow_html=True)
            with st.expander(title, expanded=True):
                fn(output)

    # ── Download Excel button ─────────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown(f'<hr style="border-color:{BORDER};opacity:.5">', unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    _, dl_col, _ = st.columns([2, 3, 2])
    with dl_col:
        if os.path.exists(output["report_path"]):
            with open(output["report_path"], "rb") as f:
                st.download_button(
                    label     = "Download Excel Report",
                    data      = f,
                    file_name = "FinanceFlow_Variance_Report.xlsx",
                    mime      = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True,
                )
        ai = output["commentary"]["ai_used"]
        st.markdown(
            f'<div style="text-align:center;margin-top:10px;" class="stCaption">'
            f'Commentary: {"Claude AI" if ai else "template fallback"} &nbsp;·&nbsp; '
            f'3-tab Excel workbook with live formulas</div>',
            unsafe_allow_html=True,
        )

    # ── Analyse different files ───────────────────────────────────────────────
    st.markdown("<br><br>", unsafe_allow_html=True)
    _, rc, _ = st.columns([2, 3, 2])
    with rc:
        if st.button("Analyse different files", key="restart", use_container_width=True):
            for key in ["settings", "pipeline_output", "dashboard_animated", "chat_history"]:
                st.session_state.pop(key, None)
            st.rerun()

    # ── Nav click handlers (placed at bottom so they add no space near top) ───
    _nav_aids_json = json.dumps([_anchor_id(t) for t in active_titles])
    components.html(f"""<script>
(function(){{
  var d = window.parent.document;
  function attach(){{
    // Fix the top gap: measure stMain's actual margin and adjust the spacer
    var main = d.querySelector('section[data-testid="stMain"]') || d.body;
    var spacer = d.getElementById('ff-spacer');
    if(spacer && main){{
      var marginTop = parseFloat(window.parent.getComputedStyle(main).marginTop) || 0;
      var newHeight = Math.max(0, 140 + 15 - marginTop);
      spacer.style.height = newHeight + 'px';
    }}

    var h = d.getElementById('ff-nav-home');
    if(h) h.onclick = function(){{
      window.parent.location.href =
        window.parent.location.origin + window.parent.location.pathname;
    }};
    var aids = {_nav_aids_json};
    aids.forEach(function(aid, i){{
      var el = d.getElementById('ff-nav-'+i);
      if(!el) return;
      el.onclick = function(){{
        var target = d.getElementById(aid);
        if(!target) return;
        var mRect = main.getBoundingClientRect();
        var tRect = target.getBoundingClientRect();
        main.scrollTo({{top: main.scrollTop+(tRect.top-mRect.top)-155, behavior:'smooth'}});
      }};
    }});
  }}
  setTimeout(attach, 400);
}})();
</script>""", height=1)


# ═════════════════════════════════════════════════════════════════════════════
# MAIN — state machine
# ═════════════════════════════════════════════════════════════════════════════

def main():
    # State 1: No settings yet → show landing / upload page
    if "settings" not in st.session_state:
        result = _landing()
        if result:
            st.session_state["settings"] = result
            st.rerun()
        return

    # State 2: Settings saved but pipeline not run yet → run it
    if "pipeline_output" not in st.session_state:
        _run_analysis(st.session_state["settings"])
        return

    # State 3: Pipeline done → show dashboard
    _dashboard(st.session_state["pipeline_output"])


main()
