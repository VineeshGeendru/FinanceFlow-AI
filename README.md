# FinanceFlow-AI

> AI-powered FP&A variance analysis that cuts month-end close commentary from 4–6 hours to 30 minutes.

Built by Vineesh Geendru and Ranadheer Reddy Aienala as a finance and technology collaboration combining FP&A domain knowledge with data engineering, analytics automation, dashboarding, Excel reporting, and AI-generated variance commentary.

---

## The Problem

Every month-end, finance teams receive actuals from accounting, compare them to budget, chase department heads for variance explanations, and write commentary for the CFO. It takes 4–6 hours of manual work across spreadsheets, emails, and slide decks.

FinanceFlow-AI automates every step — load your files, get back a dashboard and a formatted Excel report with AI-generated commentary, ready to distribute.

---

## What It Produces

**Upload two files. Get back:**

* An interactive web dashboard with a fixed navigation bar, KPI cards, and six analysis sections
* A **three-tab Excel workbook** — Executive Summary, YTD Variance Analysis, and Monthly Detail — with live formulas and conditional formatting
* A **chase list** of material variances missing budget owner explanations, so you know exactly whose inbox to hit before the report goes out

**Dashboard sections:**

| Section                           | What it shows                                                                                            |
| --------------------------------- | -------------------------------------------------------------------------------------------------------- |
| Operating Income Bridge           | Waterfall chart — how Revenue, COGS, and Opex variances combine into the OI miss or beat                 |
| Anomaly Detection                 | Spikes, consecutive deterioration trends, and material variances with no driver note on file             |
| Year-End Forecast Projection      | Full-year P&L forecast: YTD actuals + remaining months at budget, with KPI cards and a grouped bar chart |
| Variance Heatmap                  | Line item × month grid colored by net impact on Operating Income                                         |
| Budget vs Actual — Trend Explorer | Month-by-month line chart for any line item, with material-month markers                                 |
| YTD Variance Detail               | Filterable table of every line item with AI-generated commentary                                         |

---

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Set your API key

This step is optional. The tool works without an API key.

```bash
cp .env.example .env
# Open .env and paste your Anthropic API key
```

Without a key, the tool falls back to deterministic template commentary. The pipeline always completes.

### 3. Run the dashboard

```bash
streamlit run app.py
```

Open `http://localhost:8501`.

Upload your Budget and Actuals files on the landing page and click **Run Analysis**. Or check **Use demo data** to explore a sample SaaS company dataset immediately.

---

## Required File Format

Budget and actuals files (`.xlsx` or `.csv`) must have exactly these five columns:

| Column       | Type                            | Example               |
| ------------ | ------------------------------- | --------------------- |
| `Month`      | String — YYYY-MM                | `2026-01`             |
| `Department` | String                          | `Engineering`         |
| `Line Item`  | String                          | `Salaries & Benefits` |
| `Category`   | String — Revenue, COGS, or Opex | `Opex`                |
| `Amount`     | Number, no currency symbols     | `315000`              |

The drivers file (`.csv`, optional) collects budget owner explanations:

| Column        | Example                                                                                        |
| ------------- | ---------------------------------------------------------------------------------------------- |
| `Month`       | `2026-03`                                                                                      |
| `Department`  | `Engineering`                                                                                  |
| `Line Item`   | `Salaries & Benefits`                                                                          |
| `Driver Note` | `Hired 3 senior engineers ahead of H2 roadmap; approved by CTO outside original budget cycle.` |

The tool validates all files before running and returns clear, actionable error messages if anything is wrong — wrong format, missing columns, non-numeric amounts, month format mismatches, or corrupt files.

---

## Architecture

```text
data/
  budget_fy2026.xlsx    ← full-year plan
  actuals_2026.xlsx     ← closed months (Jan-Jun)
  drivers.csv           ← budget owner explanations

src/
  config.py             ← all thresholds, model settings, paths in one place
  data_loader.py        ← load, validate, detect closed months, slice budget
  variance_engine.py    ← merge, compute variances, sign logic, materiality,
                           YTD rollup, P&L summary, anomaly detection
  commentary.py         ← Claude API prompts + template fallback
  report_builder.py     ← three-tab Excel report with live formulas
  main.py               ← shared pipeline function + CLI entry point

app.py                  ← Streamlit dashboard
output/                 ← generated reports, gitignored
```

**Pipeline flow:**

```text
load_data()  →  run_variance_engine()  →  generate_commentary()  →  build_report()
     ↑                                                                      ↓
validate files                                              FinanceFlow_Variance_Report.xlsx
detect closed months                                        + Streamlit dashboard
```

---

## Key Design Decisions

### Match only closed months, not the full year

The tool detects which months exist in the actuals file and slices the budget to match. Comparing actuals against future budget months would produce 100% unfavorable variances for every line item that hasn't happened yet — meaningless noise. Matching closed months means the analysis reflects real performance, not calendar math.

### Dual materiality threshold

A variance is flagged as material if it clears **either** a dollar threshold or a percent-of-budget threshold.

Default thresholds:

* Dollar threshold: $25K
* Percent threshold: 5%

Dollar-only misses a 50% overrun on a small line. Percent-only misses a 1% miss on a $10M line that amounts to $100K. Both thresholds are configurable in `src/config.py`.

### AI only reads computed numbers, never raw data

The Claude API receives only the variance amounts the engine already calculated, plus the exact text from the drivers file. It cannot see the raw Excel files. This prevents the AI from inventing variance causes — it can only attribute explanations to what budget owners actually submitted.

If no driver note exists, the AI says exactly:

```text
Driver pending budget owner input.
```

### Favorable and unfavorable sign logic

`Variance $` = Actual - Budget for every line item.

But whether a positive number is good or bad depends on what it measures. For Revenue, positive variance is favorable because the company earned more than budget. For costs, including COGS and Opex, positive variance is unfavorable because the company spent more than budget.

The engine computes a `Net Impact $` column that translates everything into one language — impact on Operating Income — so favorable always means OI is better than budget.

### Live Excel formulas, not hardcoded values

Variance columns in the Excel report use formulas instead of hardcoded computed numbers.

Example:

```excel
=F2-E2
```

If a finance team member corrects an Actual value after delivery, the variance recalculates automatically. Hardcoded values would break the moment anyone edits a cell.

### Validation at the front door

Every file is validated before any computation runs. The tool checks for:

* Required columns
* Numeric Amount values
* YYYY-MM month format
* Non-empty data
* Budget and actuals month overlap
* Corrupt or unreadable files

If anything is wrong, a clear error message names the exact problem and how to fix it. The user never sees a Python traceback.

Individual dashboard sections also fail gracefully. If one chart errors, the rest of the dashboard still renders.

---

## Tech Stack

| Tool                  | Purpose                                              |
| --------------------- | ---------------------------------------------------- |
| Python                | Core language                                        |
| pandas                | Data loading, merging, aggregation, variance math    |
| openpyxl              | Excel report generation with formulas and formatting |
| Streamlit             | Web dashboard                                        |
| Plotly                | Waterfall, heatmap, trend charts                     |
| Claude API, Anthropic | AI variance commentary and executive summary         |
| python-dotenv         | API key management                                   |

---

## Project Structure by Phase

| Phase | What was built                                                                                                                            |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------- |
| 1     | `explore.py` — 10 pandas analyst moves on the demo data                                                                                   |
| 2     | `src/data_loader.py` — file validation, closed-month detection                                                                            |
| 3     | `src/variance_engine.py` — variances, sign logic, materiality, P&L, anomalies                                                             |
| 4     | `src/commentary.py` — Claude API prompts with hallucination controls                                                                      |
| 5     | `src/report_builder.py` — three-tab Excel report                                                                                          |
| 6     | `src/main.py` — CLI orchestrator and shared pipeline function                                                                             |
| 7     | `app.py` — Streamlit dashboard: charts, tables, KPI cards, waterfall, heatmap, trend explorer, forecast projection                        |
| 8     | `app.py` — browser file upload, fixed two-tier navbar with section scroll, Three.js loading overlay                                       |
| 9     | `app.py`, `src/data_loader.py` — bulletproof error handling: corrupt files, missing columns, wrong formats, section-level fault isolation |

---

## Co-Authors

### Vineesh Geendru

MS Finance, C.T. Bauer College of Business, University of Houston

[LinkedIn](https://linkedin.com) · [GitHub](https://github.com/VineeshGeendru)

### Ranadheer Reddy Aienala

MS MIS Graduate, C.T. Bauer College of Business, University of Houston

[LinkedIn](https://www.linkedin.com/in/ranadheeraienala) · [GitHub](https://github.com/raienala) · [Email](mailto:ranadheerreddyaienala@gmail.com)
