"""
variance_engine.py — Compute variances, sign logic, materiality, YTD, P&L, anomalies.

WHAT IT DOES (in finance terms):
  This is the engine room of the tool. It takes the clean data from the loader
  and produces every number that appears on the dashboard or in the report:
    - Line-by-line dollar and percent variances
    - Favorable / unfavorable classification (sign logic)
    - Materiality flags ($25K or 5% thresholds)
    - YTD rollup (all closed months summed per line item)
    - P&L summary (Revenue → COGS → Gross Profit → Opex → Operating Income)
    - Anomaly detection (spikes, trends, missing drivers)

WHY IT MATTERS:
  Every CFO question — "where did we miss?" "is this trend getting worse?"
  "how does this affect operating income?" — is answered by this module.
  The dashboard, the AI commentary, and the Excel report all read from the
  DataFrames this module produces. If the math here is wrong, everything
  downstream is wrong.

INTERVIEW ANGLE:
  "Walk me through how you compute the variance and determine if it's
  favorable or unfavorable."
  Answer: sign logic — covered in detail below.
"""

import pandas as pd
import numpy as np
from src.config import (
    MATERIALITY_THRESHOLD_DOLLARS,
    MATERIALITY_THRESHOLD_PERCENT,
    ANOMALY_SPIKE_MULTIPLIER,
)


# ── Main entry point ──────────────────────────────────────────────────────────

def run_variance_engine(data: dict) -> dict:
    """
    Takes the dict returned by load_data() and returns a dict with:
      "monthly"     — row-by-row variance table (one row per month per line item)
      "ytd"         — YTD rollup (one row per line item, all months summed)
      "pl_summary"  — P&L summary (Revenue, COGS, Gross Profit, Opex, Op Income)
      "anomalies"   — DataFrame of flagged anomalies with descriptions
    """
    monthly    = _compute_variances(data["budget_closed"], data["actuals"])
    monthly    = _apply_sign_logic(monthly)
    monthly    = _flag_materiality(monthly)

    ytd        = _build_ytd_rollup(monthly)
    pl_summary = _build_pl_summary(monthly)
    anomalies  = _detect_anomalies(monthly, data["drivers"])

    return {
        "monthly":    monthly,
        "ytd":        ytd,
        "pl_summary": pl_summary,
        "anomalies":  anomalies,
    }


# ── Step 1: Merge and compute raw variance ────────────────────────────────────

def _compute_variances(budget_closed: pd.DataFrame, actuals: pd.DataFrame) -> pd.DataFrame:
    """
    Merge budget and actuals on the four key columns, then compute dollar
    and percent variance.

    WHAT THIS IS LIKE IN EXCEL:
      Imagine two tables side by side, joined on Month + Department +
      Line Item + Category. That's a VLOOKUP on four keys at once.
      Then you add a column: =Actual - Budget.  That's all this is.

    WHY INNER JOIN:
      If a line item exists in actuals but not in budget (or vice versa),
      we can't compute a meaningful variance — we'd be dividing by zero
      or comparing against nothing.  Inner join drops those orphan rows
      and we warn about them in the data loader.
    """
    df = budget_closed.merge(
        actuals,
        on=["Month", "Department", "Line Item", "Category"],
        suffixes=("_budget", "_actual"),
        how="inner",
    )

    df["Variance $"] = df["Amount_actual"] - df["Amount_budget"]

    # Percent variance: how far off budget are we, as a fraction of budget?
    # Guard against budget = 0 (would produce divide-by-zero → infinity).
    df["Variance %"] = df.apply(
        lambda row: (row["Variance $"] / row["Amount_budget"] * 100)
        if row["Amount_budget"] != 0 else 0.0,
        axis=1,
    )

    return df


# ── Step 2: Sign logic — the most important finance concept in this project ───

def _apply_sign_logic(df: pd.DataFrame) -> pd.DataFrame:
    """
    Determine whether each variance is Favorable or Unfavorable, and
    compute the Net Impact on Operating Income.

    THIS IS THE CONCEPT INTERVIEWERS TEST MOST.  Read this carefully.

    ─────────────────────────────────────────────────────────────────────
    THE CORE INSIGHT:
      "Variance $" = Actual - Budget  (always the same formula)
      But whether that number is GOOD or BAD depends on what it's measuring.

    REVENUE:
      Budget Revenue = $905K.  Actual Revenue = $810K.
      Variance $ = -$95K  →  UNFAVORABLE  (you earned less than planned)
      A negative revenue variance hurts the company.

      Budget Revenue = $820K.  Actual Revenue = $824K.
      Variance $ = +$4K  →  FAVORABLE  (you earned more than planned)
      A positive revenue variance helps the company.

    COSTS (COGS and Opex):
      Budget Salaries = $300K.  Actual Salaries = $370K.
      Variance $ = +$70K  →  UNFAVORABLE  (you spent more than planned)
      A positive cost variance hurts the company — you're over budget.

      Budget Cloud = $125K.  Actual Cloud = $107K.
      Variance $ = -$18K  →  FAVORABLE  (you spent less than planned)
      A negative cost variance helps the company — you're under budget.

    RULE:
      Revenue:      positive variance = Favorable
      COGS / Opex:  negative variance = Favorable  (opposite direction)

    NET IMPACT ON OPERATING INCOME:
      The net impact tells you: does this variance help or hurt the bottom line?
      Revenue:  Net Impact =  Variance $   (earn $4K more → OI goes up $4K)
      COGS:     Net Impact = -Variance $   (spend $70K more → GP drops $70K)
      Opex:     Net Impact = -Variance $   (spend $70K more → OI drops $70K)

      Net Impact > 0  =  Favorable  (OI is better than budget)
      Net Impact < 0  =  Unfavorable (OI is worse than budget)
    ─────────────────────────────────────────────────────────────────────
    """
    cost_categories = {"COGS", "Opex"}

    df["Net Impact $"] = df.apply(
        lambda row: row["Variance $"] if row["Category"] == "Revenue"
        else -row["Variance $"],
        axis=1,
    )

    df["Favorable"] = df["Net Impact $"] > 0

    df["F/U"] = df["Favorable"].map({True: "Favorable", False: "Unfavorable"})

    return df


# ── Step 3: Materiality flags ─────────────────────────────────────────────────

def _flag_materiality(df: pd.DataFrame) -> pd.DataFrame:
    """
    Mark a variance as "material" if it clears EITHER threshold:
      - Absolute dollar variance >= $25K  (default from config)
      - Percent variance >= 5% of budget  (default from config)

    WHY BOTH THRESHOLDS:
      Dollar only: a 20% miss on a $50K line ($10K) would slip through.
      Percent only: a 0.5% miss on a $10M line ($50K) would slip through.
      Using EITHER catches big % variances on small lines AND big $ variances
      on large lines.  This mirrors how most FP&A teams set escalation rules.

    INTERVIEW ANGLE:
      "How do you decide what's material?"
      Answer: configurable dual threshold — absolute dollar OR percent of
      budget — because each catches a class of variances the other misses.
    """
    df["Material"] = (
        (df["Variance $"].abs() >= MATERIALITY_THRESHOLD_DOLLARS) |
        (df["Variance %"].abs() >= MATERIALITY_THRESHOLD_PERCENT)
    )

    return df


# ── Step 4: YTD rollup ────────────────────────────────────────────────────────

def _build_ytd_rollup(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Sum all closed months for each unique Department + Line Item + Category
    combination.  This is the YTD view — "how are we doing for the year so far?"

    WHAT THIS IS LIKE IN EXCEL:
      Like adding a "YTD" row at the bottom of each section in your
      budget vs actual report — but doing it for every single line item
      automatically.

    WHY NOT JUST FILTER THE MONTHLY TABLE:
      Materiality at the monthly level can be noisy — a $30K spike in
      March might reverse in April.  YTD materiality tells you whether
      the cumulative impact is significant, which is what leadership cares
      about when asking "are we on track for the year?"
    """
    ytd = monthly.groupby(
        ["Department", "Line Item", "Category"], as_index=False
    ).agg(
        YTD_Budget = ("Amount_budget", "sum"),
        YTD_Actual = ("Amount_actual", "sum"),
        YTD_Var    = ("Variance $",    "sum"),
        YTD_NetImp = ("Net Impact $",  "sum"),
    )

    ytd["YTD_Var_Pct"] = ytd.apply(
        lambda row: (row["YTD_Var"] / row["YTD_Budget"] * 100)
        if row["YTD_Budget"] != 0 else 0.0,
        axis=1,
    )

    ytd["YTD_Favorable"] = ytd["YTD_NetImp"] > 0
    ytd["YTD_FU"]        = ytd["YTD_Favorable"].map({True: "Favorable", False: "Unfavorable"})

    ytd["YTD_Material"] = (
        (ytd["YTD_Var"].abs() >= MATERIALITY_THRESHOLD_DOLLARS) |
        (ytd["YTD_Var_Pct"].abs() >= MATERIALITY_THRESHOLD_PERCENT)
    )

    ytd = ytd.sort_values("YTD_NetImp")  # worst impact first

    return ytd


# ── Step 5: P&L summary ───────────────────────────────────────────────────────

def _build_pl_summary(monthly: pd.DataFrame) -> pd.DataFrame:
    """
    Roll up the full variance table into a P&L income statement structure:
      Revenue
    - COGS
    = Gross Profit
    - Opex
    = Operating Income

    WHY THIS ORDER MATTERS:
      This is how a real income statement reads.  When you show the CFO
      the summary page, they expect to see it in this exact structure —
      not a flat list of categories in alphabetical order.  The waterfall
      chart in the dashboard maps directly onto these five rows.

    INTERVIEW ANGLE:
      "How do you compute Gross Profit and Operating Income in your tool?"
      Answer: Revenue minus COGS for GP; GP minus Opex for OI.  I build
      those as derived rows in the P&L summary after aggregating the
      individual line items by category.
    """
    totals = monthly.groupby("Category").agg(
        Budget = ("Amount_budget", "sum"),
        Actual = ("Amount_actual", "sum"),
    ).reset_index()

    # Convert to a dict for easy lookup
    t = {row["Category"]: row for _, row in totals.iterrows()}

    def safe_get(category, col):
        return t[category][col] if category in t else 0

    revenue_bud = safe_get("Revenue", "Budget")
    revenue_act = safe_get("Revenue", "Actual")
    cogs_bud    = safe_get("COGS",    "Budget")
    cogs_act    = safe_get("COGS",    "Actual")
    opex_bud    = safe_get("Opex",    "Budget")
    opex_act    = safe_get("Opex",    "Actual")

    gp_bud = revenue_bud - cogs_bud
    gp_act = revenue_act - cogs_act
    oi_bud = gp_bud - opex_bud
    oi_act = gp_act - opex_act

    rows = [
        ("Revenue",          revenue_bud, revenue_act),
        ("COGS",             cogs_bud,    cogs_act),
        ("Gross Profit",     gp_bud,      gp_act),
        ("Opex",             opex_bud,    opex_act),
        ("Operating Income", oi_bud,      oi_act),
    ]

    pl = pd.DataFrame(rows, columns=["Line", "Budget", "Actual"])
    pl["Variance $"] = pl["Actual"] - pl["Budget"]
    pl["Variance %"] = pl.apply(
        lambda row: (row["Variance $"] / row["Budget"] * 100)
        if row["Budget"] != 0 else 0.0,
        axis=1,
    )

    # For the P&L, favorable means: Revenue/GP/OI variance is positive,
    # COGS/Opex variance is negative (same sign logic as individual lines).
    cost_lines = {"COGS", "Opex"}
    pl["Net Impact $"] = pl.apply(
        lambda row: row["Variance $"] if row["Line"] not in cost_lines
        else -row["Variance $"],
        axis=1,
    )
    pl["F/U"] = pl["Net Impact $"].apply(
        lambda x: "Favorable" if x > 0 else ("Unfavorable" if x < 0 else "On Budget")
    )

    return pl


# ── Step 6: Anomaly detection ─────────────────────────────────────────────────

def _detect_anomalies(monthly: pd.DataFrame, drivers: pd.DataFrame) -> pd.DataFrame:
    """
    Flag unusual patterns that a human scanning a 72-row table would likely miss.

    THREE ANOMALY TYPES:

    1. SPIKE — a single month's variance is unusually large relative to that
       line item's own history.  E.g., Subscription Revenue's May variance is
       3.4x larger than any other month's variance for that line.
       WHY IT MATTERS: spikes often signal one-time events (a customer churn,
       an early payment) that need specific explanation, not just "trending up."

    2. CONSECUTIVE DETERIORATION — a line item has been unfavorable for 3+
       months in a row, getting worse each month.
       WHY IT MATTERS: a single bad month is noise; three consecutive months
       getting worse is a trend that needs a management response, not a footnote.

    3. MATERIAL + NO DRIVER — a line item is material (cleared $25K or 5%
       threshold) but has no entry in the drivers file.
       WHY IT MATTERS: this is the "chase list" — exactly whose inbox you need
       to hit before the CFO deck goes out.  The AI will also note this as
       "driver pending budget owner input" in commentary.
    """
    anomalies = []

    for (dept, line_item, category), group in monthly.groupby(
        ["Department", "Line Item", "Category"]
    ):
        group = group.sort_values("Month")
        variances = group["Variance $"].abs()

        # ── Anomaly 1: Spike ──────────────────────────────────────────────────
        # Only flag spikes where the average monthly variance is at least $5K —
        # otherwise a $400 spike on a $200-average line creates noise, not signal.
        if len(variances) >= 2:
            mean_var = variances.mean()
            max_var  = variances.max()
            if mean_var >= 5_000 and max_var / mean_var >= ANOMALY_SPIKE_MULTIPLIER:
                spike_month = group.loc[variances.idxmax(), "Month"]
                spike_amt   = group.loc[variances.idxmax(), "Variance $"]
                anomalies.append({
                    "Type":        "Spike",
                    "Department":  dept,
                    "Line Item":   line_item,
                    "Category":    category,
                    "Month":       spike_month,
                    "Description": (
                        f"{line_item} in {dept}: single-month variance of "
                        f"${spike_amt:+,.0f} in {spike_month} is "
                        f"{max_var / mean_var:.1f}x the average monthly variance "
                        f"for this line item."
                    ),
                })

        # ── Anomaly 2: Consecutive deterioration (3+ months worsening) ────────
        net_impacts = group["Net Impact $"].tolist()
        if len(net_impacts) >= 3:
            streak = 1
            for i in range(1, len(net_impacts)):
                if net_impacts[i] < net_impacts[i - 1]:  # getting worse
                    streak += 1
                else:
                    streak = 1
                if streak >= 3:
                    months_range = f"{group['Month'].iloc[i-streak+2]} to {group['Month'].iloc[i]}"
                    anomalies.append({
                        "Type":        "Consecutive Deterioration",
                        "Department":  dept,
                        "Line Item":   line_item,
                        "Category":    category,
                        "Month":       group["Month"].iloc[i],
                        "Description": (
                            f"{line_item} in {dept}: net impact on operating income "
                            f"has worsened for {streak} consecutive months "
                            f"({months_range})."
                        ),
                    })
                    break  # one flag per line item is enough

        # ── Anomaly 3: Material variance with no driver note ──────────────────
        material_rows = group[group["Material"]]
        for _, row in material_rows.iterrows():
            has_driver = (
                not drivers.empty and
                len(drivers[
                    (drivers["Month"]       == row["Month"]) &
                    (drivers["Department"]  == dept) &
                    (drivers["Line Item"]   == line_item)
                ]) > 0
            )
            if not has_driver:
                anomalies.append({
                    "Type":        "Missing Driver",
                    "Department":  dept,
                    "Line Item":   line_item,
                    "Category":    category,
                    "Month":       row["Month"],
                    "Description": (
                        f"{line_item} in {dept} ({row['Month']}): "
                        f"material variance of ${row['Variance $']:+,.0f} "
                        f"({row['Variance %']:+.1f}% vs budget) — "
                        f"no driver note on file. Chase budget owner for explanation."
                    ),
                })

    if not anomalies:
        return pd.DataFrame(columns=["Type", "Department", "Line Item",
                                     "Category", "Month", "Description"])

    return pd.DataFrame(anomalies).sort_values(
        ["Type", "Department", "Line Item", "Month"]
    ).reset_index(drop=True)
