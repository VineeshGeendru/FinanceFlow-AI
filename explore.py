"""
FinanceFlow-AI | Phase 1: Analyst Exploration
==============================================
This file is your sandbox. Think of it as Excel for a finance analyst,
but with superpowers. Each section is one "analyst move" — a technique
you will use constantly in FP&A work and in this project.

Run the whole file with:  py explore.py
Or run one section at a time in VS Code with the Run Cell button (# %%)

DATA REMINDER:
  budget_fy2026.xlsx  →  144 rows, 12 months (full year plan)
  actuals_2026.xlsx   →   72 rows,  6 months (Jan–Jun closed)
  drivers.csv         →    5 rows  (budget owner explanations)
"""

import pandas as pd

# ── Load once, use everywhere ─────────────────────────────────────────────────
budget  = pd.read_excel("data/budget_fy2026.xlsx")
actuals = pd.read_excel("data/actuals_2026.xlsx")
drivers = pd.read_csv("data/drivers.csv")

print("Files loaded.\n")


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 1 — Get your bearings  (Excel: Ctrl+End to find the last row, then scan)
# ══════════════════════════════════════════════════════════════════════════════
print("=" * 60)
print("MOVE 1 — Shape, columns, data types")
print("=" * 60)

print(f"\nBudget:  {budget.shape[0]} rows × {budget.shape[1]} columns")
print(f"Actuals: {actuals.shape[0]} rows × {actuals.shape[1]} columns")
print(f"\nColumn names:  {list(budget.columns)}")
print(f"\nData types:\n{budget.dtypes}")
print(f"\nFirst 5 rows of actuals:\n{actuals.head()}")

# WHY THIS MATTERS: Before you do any analysis, you need to know what you have.
# Shape tells you if rows are missing. dtypes catch silent errors — e.g., if
# Amount loaded as a string ("1,200,000") instead of a number, every sum
# you run will be wrong.  This is the first thing auditors check.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 2 — Filter rows  (Excel: Data → Filter, then click a value)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 2 — Filter: show only Revenue rows")
print("=" * 60)

revenue_actuals = actuals[actuals["Category"] == "Revenue"]
print(revenue_actuals.to_string(index=False))

# You can stack filters just like stacking Excel filters:
eng_opex = budget[
    (budget["Department"] == "Engineering") &
    (budget["Category"] == "Opex")
]
print(f"\nEngineering Opex budget rows: {len(eng_opex)}")

# WHY THIS MATTERS: The data file mixes Revenue, COGS, and Opex in one table.
# Every meaningful FP&A question scopes to a category or department first.
# If you forget to filter, your totals include apples and oranges.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 3 — Sort  (Excel: Data → Sort)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 3 — Sort: largest actual spend items first")
print("=" * 60)

top_spend = actuals.sort_values("Amount", ascending=False).head(10)
print(top_spend[["Month", "Department", "Line Item", "Amount"]].to_string(index=False))

# WHY THIS MATTERS: In a real month-end review, you start with the biggest
# numbers. If the CFO asks "where did we overspend?" you want the top items
# immediately, not buried in alphabetical order.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 4 — GroupBy sum  (Excel: SUMIF or pivot table with one row field)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 4 — GroupBy: total actuals by Department")
print("=" * 60)

by_dept = actuals.groupby("Department")["Amount"].sum().sort_values(ascending=False)
print(by_dept.to_string())

print("\nHIGHEST SPEND DEPARTMENT:", by_dept.index[0],
      f"  (${by_dept.iloc[0]:,.0f})")

# WHY THIS MATTERS: This is SUMIF on a whole column at once. In Excel you'd
# write =SUMIF($B:$B,"Engineering",$E:$E) six times. Here you get all
# departments in one line, sorted, ready to paste into a slide.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 5 — GroupBy by Month  (Excel: pivot with Month in rows)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 5 — Total actuals Amount by Month")
print("=" * 60)

by_month = actuals.groupby("Month")["Amount"].sum().reset_index()
by_month.columns = ["Month", "Total Actuals"]
by_month["Total Actuals"] = by_month["Total Actuals"].map("${:,.0f}".format)
print(by_month.to_string(index=False))

# WHY THIS MATTERS: Month-over-month trend is the first thing you show in a
# CFO pack. Grouping by Month builds that trend table in one line.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 6 — Pivot table  (Excel: Insert → PivotTable)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 6 — Pivot: Department × Month actuals heatmap")
print("=" * 60)

pivot = actuals.pivot_table(
    index="Department",
    columns="Month",
    values="Amount",
    aggfunc="sum",
    fill_value=0
)
# Format as dollars for readability
pivot_fmt = pivot.map(lambda x: f"${x:,.0f}")
print(pivot_fmt.to_string())

# WHY THIS MATTERS: This is the exact table that becomes the "variance heatmap"
# in the Streamlit dashboard. You can swap index/columns to rotate the view —
# pivot_table is pivot table, period.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 7 — Merge  (Excel: VLOOKUP on multiple columns, or INDEX/MATCH)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 7 — Merge budget + actuals (the variance table foundation)")
print("=" * 60)

# Only closed months (Jan–Jun) exist in actuals. We filter budget to match
# so we don't compare actuals against future budget months.
closed_months = actuals["Month"].unique()
budget_closed = budget[budget["Month"].isin(closed_months)]

merged = budget_closed.merge(
    actuals,
    on=["Month", "Department", "Line Item", "Category"],
    suffixes=("_budget", "_actual"),
    how="inner"
)
print(f"Budget rows (closed months only): {len(budget_closed)}")
print(f"Actuals rows:                     {len(actuals)}")
print(f"Merged rows:                      {len(merged)}")
print(f"\nFirst 5 merged rows:\n{merged.head().to_string(index=False)}")

# WHY THIS MATTERS: This is like doing VLOOKUP on FOUR keys at once (Month,
# Department, Line Item, Category). If any key doesn't match, that row drops
# out. The merge is the foundation of every variance report.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 8 — Add computed columns  (Excel: formula column)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 8 -- Add Variance column  (Actual - Budget)")
print("=" * 60)

merged["Variance $"] = merged["Amount_actual"] - merged["Amount_budget"]
merged["Variance %"] = merged["Variance $"] / merged["Amount_budget"] * 100

# Show the most negative (worst overspend on cost / largest revenue miss)
worst = merged.sort_values("Variance $").head(5)
print(worst[["Month", "Department", "Line Item", "Category",
             "Amount_budget", "Amount_actual", "Variance $", "Variance %"]].to_string(index=False))

# ANSWER: one column to add to the merged table → "Variance $" (Actual minus Budget)
# That single column turns a data table into a variance report.

# WHY THIS MATTERS: Interviewers often ask "how would you compute variance?"
# The answer is simple: merge on your keys, then subtract. Everything else
# (sign logic, materiality flags, % calc) builds on top of this column.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 9 — Multi-level aggregation  (Excel: pivot with multiple value fields)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 9 — YTD summary: Budget, Actual, Variance by Category")
print("=" * 60)

ytd_summary = merged.groupby("Category").agg(
    YTD_Budget  = ("Amount_budget",  "sum"),
    YTD_Actual  = ("Amount_actual",  "sum"),
    YTD_Variance= ("Variance $",     "sum")
).reset_index()
ytd_summary["Var %"] = ytd_summary["YTD_Variance"] / ytd_summary["YTD_Budget"] * 100

print(ytd_summary.to_string(index=False))

# WHY THIS MATTERS: This is the YTD summary slide that goes to the CFO.
# agg() lets you compute multiple metrics at once — equivalent to a pivot
# table that shows Sum of Budget, Sum of Actual, and Sum of Variance
# in three separate columns.


# ══════════════════════════════════════════════════════════════════════════════
# MOVE 10 — Export to CSV and Excel  (Excel: Save As)
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("MOVE 10 — Export: save the merged variance table")
print("=" * 60)

import os
os.makedirs("output", exist_ok=True)

merged.to_csv("output/variance_explore.csv", index=False)
print("Saved: output/variance_explore.csv")

# WHY THIS MATTERS: Every output this tool produces gets saved to output/.
# That way anyone can open the CSV in Excel, review it, or feed it into
# another system. Automation that can't export is automation no one trusts.


# ══════════════════════════════════════════════════════════════════════════════
# FOUR ANALYST QUESTIONS — ANSWERED
# ══════════════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("FOUR ANALYST QUESTIONS — ANSWERED")
print("=" * 60)

# Q1: Total YTD actual Revenue
ytd_revenue = actuals[actuals["Category"] == "Revenue"]["Amount"].sum()
print(f"\nQ1 — Total YTD Actual Revenue:  ${ytd_revenue:,.0f}")

# Q2: Highest-spend department (by total actuals across all categories)
highest_dept = actuals.groupby("Department")["Amount"].sum().idxmax()
highest_amt  = actuals.groupby("Department")["Amount"].sum().max()
print(f"Q2 — Highest-Spend Department:  {highest_dept}  (${highest_amt:,.0f})")

# Q3: Total actuals by month
print("\nQ3 — Total Actuals by Month:")
for _, row in actuals.groupby("Month")["Amount"].sum().reset_index().iterrows():
    print(f"     {row['Month']}:  ${row['Amount']:,.0f}")

# Q4: One column to add to the merged table
print("\nQ4 -- One column to add:  'Variance $'  (Actual - Budget)")
print("     That single formula turns the merged table into a variance report.")
print("     Everything else -- % variance, materiality flags, sign logic --")
print("     builds on top of that one column.\n")
