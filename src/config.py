"""
config.py — Single place to change any setting in the tool.

WHY THIS EXISTS:
  Every threshold, path, and model name lives here — not buried inside
  engine code.  When a new company uses this tool and wants $50K materiality
  instead of $25K, they change ONE line here, nothing else.

INTERVIEW ANGLE:
  "How would you adapt this tool for a different company?"
  Answer: change config.py.  The engine code never needs to be touched.
"""

# ── Materiality thresholds ────────────────────────────────────────────────────
# A variance is "material" (worth flagging) if it clears EITHER bar.
# Default: $25K absolute dollar swing OR 5% of the budget line.
# These match typical FP&A escalation rules — small % on a big line can still
# be significant in dollars, and a big % on a tiny line is noise.
MATERIALITY_THRESHOLD_DOLLARS  = 25_000   # absolute dollar variance
MATERIALITY_THRESHOLD_PERCENT  = 5.0      # % of budget amount

# ── Anomaly detection ─────────────────────────────────────────────────────────
# A spike is flagged when a single month's variance is this many times larger
# than the average variance for that line item across all closed months.
ANOMALY_SPIKE_MULTIPLIER = 2.0

# ── AI model ──────────────────────────────────────────────────────────────────
CLAUDE_MODEL   = "claude-haiku-4-5-20251001"   # fast + cheap for commentary
MAX_TOKENS     = 1024

# ── File paths (defaults — overridden when user uploads files in the UI) ──────
BUDGET_PATH    = "data/budget_fy2026.xlsx"
ACTUALS_PATH   = "data/actuals_2026.xlsx"
DRIVERS_PATH   = "data/drivers.csv"
OUTPUT_DIR     = "output"

# ── Report settings ───────────────────────────────────────────────────────────
REPORT_FILENAME = "FinanceFlow_Variance_Report.xlsx"

# ── Required columns (validation guard) ──────────────────────────────────────
REQUIRED_COLUMNS = ["Month", "Department", "Line Item", "Category", "Amount"]
