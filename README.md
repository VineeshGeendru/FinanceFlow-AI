# FinanceFlow-AI

> AI-powered FP&A variance analysis that cuts month-end close commentary from 4–6 hours to 30 minutes.

---

## The Problem

Every month-end, finance teams receive actuals from accounting, compare them to budget, chase department heads for variance explanations, and write commentary for the CFO. It takes 4–6 hours of manual work across spreadsheets, emails, and slide decks.

FinanceFlow-AI automates every step — load your files, get back a dashboard and a formatted Excel report with AI-generated commentary, ready to distribute.

---

## What It Produces

**Upload two files. Get back:**

- An interactive web dashboard — KPI cards, waterfall chart, variance heatmap, anomaly alerts, and a trend explorer
- A three-tab Excel workbook — Executive Summary, YTD Variance Analysis, and Monthly Detail — with live formulas and conditional formatting
- A chase list of material variances that are missing budget owner explanations, so you know exactly whose inbox to hit before the report goes out

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key (optional — the tool works without it)

```bash
cp .env.example .env
# Open .env and paste your Anthropic API key
```

Without a key, the tool falls back to deterministic template commentary. The pipeline always completes.

### 3a. Web dashboard (no terminal needed after this)

```bash
streamlit run app.py
```

Open `http://localhost:8501`, drag and drop your files in the sidebar, and click **Run Analysis**.

### 3b. Command line

```bash
py src/main.py
```

With custom files and thresholds:

```bash
py src/main.py --budget data/q3_budget.xlsx --actuals data/q3_actuals.xlsx --materiality-dollars 50000
```

### Demo data

The `data/` folder contains sample files for a fictional SaaS company (FY2026). Check **Use demo data** in the sidebar to explore the full output before uploading your own files.

---

## Required File Format

Budget and actuals files (`.xlsx` or `.csv`) must have exactly these five columns:

| Column | Type | Example |
|---|---|---|
| `Month` | String — YYYY-MM | `2026-01` |
| `Department` | String | `Engineering` |
| `Line Item` | String | `Salaries & Benefits` |
| `Category` | String — Revenue, COGS, or Opex | `Opex` |
| `Amount` | Number (no currency symbols) | `315000` |

The drivers file (`.csv`, optional) collects budget owner explanations:

| Column | Example |
|---|---|
| `Month` | `2026-03` |
| `Department` | `Engineering` |
| `Line Item` | `Salaries & Benefits` |
| `Driver Note` | `Hired 3 senior engineers ahead of H2 roadmap; approved by CTO outside original budget cycle.` |

The tool validates all files before running and raises clear, actionable errors if anything is wrong.

---

## Architecture

```
data/
  budget_fy2026.xlsx    ← full-year plan
  actuals_2026.xlsx     ← closed months (Jan–Jun)
  drivers.csv           ← budget owner explanations

src/
  config.py             ← all thresholds, model settings, paths in one place
  data_loader.py        ← load, validate, detect closed months, slice budget
  variance_engine.py    ← merge, compute variances, sign logic, materiality,
                           YTD rollup, P&L summary, anomaly detection
  commentary.py         ← Claude API prompts + template fallback
  report_builder.py     ← three-tab Excel report with live formulas
  main.py               ← shared pipeline function + CLI entry point

app.py                  ← Streamlit dashboard (calls run_pipeline from main.py)
output/                 ← generated reports (gitignored)
```

**Pipeline flow:**

```
load_data()  →  run_variance_engine()  →  generate_commentary()  →  build_report()
     ↑                                                                      ↓
validate files                                              FinanceFlow_Variance_Report.xlsx
detect closed months                                        + Streamlit dashboard
```

---

## Key Design Decisions

### Match only closed months, not the full year

The tool detects which months exist in the actuals file and slices the budget to match. Comparing actuals against future budget months would produce 100% unfavorable variances for every line item that hasn't happened yet — meaningless noise. Matching closed months means the analysis reflects real performance, not calendar math.

### Dual materiality threshold (dollar AND percent)

A variance is flagged as material if it clears **either** a dollar threshold (default: $25K) **or** a percent-of-budget threshold (default: 5%). Dollar-only misses a 50% overrun on a small line. Percent-only misses a 1% miss on a $10M line that amounts to $100K. Both thresholds are configurable in `src/config.py`.

### AI only reads computed numbers — never raw data

The Claude API receives only the variance amounts the engine already calculated, plus the exact text from the drivers file. It cannot see the raw Excel files. This prevents the AI from inventing variance causes — it can only attribute explanations to what budget owners actually submitted. If no driver note exists, the AI says exactly: *"Driver pending budget owner input."*

### Favorable/unfavorable sign logic

`Variance $` = Actual − Budget for every line item. But whether a positive number is good or bad depends on what it's measuring: for Revenue, positive variance is favorable (earned more). For costs (COGS and Opex), positive variance is unfavorable (spent more). The engine computes a `Net Impact $` column that translates everything into one language — impact on Operating Income — so favorable always means OI is better than budget.

### Live Excel formulas, not hardcoded values

Variance columns in the Excel report use formulas (`=F2-E2`) instead of the computed numbers. If a finance team member corrects an Actual value after delivery, the variance recalculates automatically. Hardcoded values would break the moment anyone edits a cell.

---

## Tech Stack

| Tool | Purpose |
|---|---|
| Python | Core language |
| pandas | Data loading, merging, aggregation, variance math |
| openpyxl | Excel report generation with formulas and formatting |
| Streamlit | Web dashboard |
| Plotly | Waterfall, heatmap, trend charts |
| Claude API (Anthropic) | AI variance commentary and executive summary |
| python-dotenv | API key management |

---

## Project Structure by Phase

| Phase | What was built |
|---|---|
| 1 | `explore.py` — 10 pandas analyst moves on the demo data |
| 2 | `src/data_loader.py` — file validation, closed-month detection |
| 3 | `src/variance_engine.py` — variances, sign logic, materiality, P&L, anomalies |
| 4 | `src/commentary.py` — Claude API prompts with hallucination controls |
| 5 | `src/report_builder.py` — three-tab Excel report |
| 6 | `src/main.py` — CLI orchestrator and shared pipeline function |
| 7 | `app.py` — Streamlit dashboard (Phase 7: charts and tables) |
| 8 | `app.py` — file upload: drag and drop in browser, no terminal needed |

---

## Author

**Vineesh Geendru**  
MS Finance, University of Houston  
Targeting FP&A and Financial Analyst roles

[LinkedIn](https://linkedin.com) · [GitHub](https://github.com/VineeshGeendru)
