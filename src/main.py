"""
main.py — Pipeline orchestrator and CLI entry point.

WHAT IT DOES (in finance terms):
  This is the "run the whole analysis" button. It calls every module in the
  right order and hands the output of each step to the next:

    1. load_data()          → validates files, detects closed months
    2. run_variance_engine()→ merges, computes variances, flags anomalies
    3. generate_commentary()→ AI or template commentary
    4. build_report()       → three-tab Excel file

  run_pipeline() is the shared function used by BOTH the CLI (this file)
  AND the Streamlit dashboard (app.py). The UI changes, the pipeline doesn't.

WHY A SHARED PIPELINE FUNCTION:
  Without it, CLI and Streamlit would each have their own copy of the four
  steps above — two places to maintain, two places to introduce bugs.
  One function, two entry points. If we fix a bug in step 2, it's fixed
  everywhere.

USAGE (from the terminal in your project folder):
  py src/main.py                                  # uses default data/ paths
  py src/main.py --budget data/q2_budget.xlsx     # custom budget file
  py src/main.py --actuals data/q2_actuals.xlsx   # custom actuals file
  py src/main.py --no-drivers                     # skip drivers file
  py src/main.py --output reports/q2_report.xlsx  # custom output path
  py src/main.py --materiality-dollars 50000      # $50K threshold
  py src/main.py --materiality-pct 10             # 10% threshold
"""

import argparse
import sys
import time
import os

# Ensure the project root is on the path so `from src.X import Y` works
# whether this file is run as `py src/main.py` or `py -m src.main`.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.data_loader      import load_data
from src.variance_engine  import run_variance_engine
from src.commentary       import generate_commentary
from src.report_builder   import build_report
import src.config as config


# ── Shared pipeline function (used by CLI and Streamlit) ─────────────────────

def run_pipeline(
    budget_path:    str   = None,
    actuals_path:   str   = None,
    drivers_path:   str   = None,
    output_path:    str   = None,
    mat_dollars:    float = None,
    mat_pct:        float = None,
) -> dict:
    """
    Run the full four-step pipeline.  All arguments are optional — defaults
    come from src/config.py so the tool works with zero arguments.

    Returns a dict with keys:
      data        — output of load_data()
      results     — output of run_variance_engine()
      commentary  — output of generate_commentary()
      report_path — path to the saved Excel file
    """
    # Override config thresholds if caller supplied them
    if mat_dollars is not None:
        config.MATERIALITY_THRESHOLD_DOLLARS = mat_dollars
    if mat_pct is not None:
        config.MATERIALITY_THRESHOLD_PERCENT = mat_pct

    budget_path  = budget_path  or config.BUDGET_PATH
    actuals_path = actuals_path or config.ACTUALS_PATH
    drivers_path = drivers_path or config.DRIVERS_PATH

    # ── Step 1: Load and validate ─────────────────────────────────────────────
    _print_step(1, "Loading and validating files")
    t0   = time.time()
    data = load_data(budget_path, actuals_path, drivers_path)
    _print_done(t0)

    _print_summary_line("Budget rows (closed months)",
                        len(data["budget_closed"]))
    _print_summary_line("Actuals rows",     len(data["actuals"]))
    _print_summary_line("Closed months",    data["closed_months"])
    _print_summary_line("Driver notes",     len(data["drivers"]))

    # ── Step 2: Variance engine ───────────────────────────────────────────────
    _print_step(2, "Computing variances")
    t0      = time.time()
    results = run_variance_engine(data)
    _print_done(t0)

    monthly   = results["monthly"]
    pl        = results["pl_summary"]
    anomalies = results["anomalies"]
    mat_count = monthly["Material"].sum()

    _print_summary_line("Total line-item rows",   len(monthly))
    _print_summary_line("Material variances",      mat_count)
    _print_summary_line("Anomalies detected",      len(anomalies))

    oi = pl[pl["Line"] == "Operating Income"].iloc[0]
    oi_dir = "below" if oi["Variance $"] < 0 else "above"
    print(f"  Operating Income:  ${oi['Actual']:>12,.0f}  "
          f"(${oi['Variance $']:+,.0f}, {oi['Variance %']:+.1f}% {oi_dir} budget)")

    # ── Step 3: Commentary ────────────────────────────────────────────────────
    _print_step(3, "Generating commentary")
    t0         = time.time()
    commentary = generate_commentary(results, data)
    _print_done(t0)

    mode = "Claude AI" if commentary["ai_used"] else "Template fallback"
    _print_summary_line("Commentary mode", mode)
    _print_summary_line("Lines with commentary",
                        len(commentary["line_commentary"]))

    # ── Step 4: Build report ──────────────────────────────────────────────────
    _print_step(4, "Building Excel report")
    t0          = time.time()
    report_path = build_report(results, commentary, output_path)
    _print_done(t0)

    # ── Final summary ─────────────────────────────────────────────────────────
    print()
    print("=" * 58)
    print("  ANALYSIS COMPLETE")
    print("=" * 58)
    _print_summary_line("Report saved to", report_path)

    if anomalies["Type"].eq("Missing Driver").any():
        missing = anomalies[anomalies["Type"] == "Missing Driver"]
        print(f"\n  ACTION REQUIRED: {len(missing)} material variance(s) "
              f"have no driver note.")
        print("  Chase budget owners for explanations before distributing.")
        for _, row in missing.drop_duplicates(
                subset=["Department", "Line Item"]).iterrows():
            print(f"    - {row['Line Item']} ({row['Department']})")
    print()

    return {
        "data":        data,
        "results":     results,
        "commentary":  commentary,
        "report_path": report_path,
    }


# ── CLI entry point ───────────────────────────────────────────────────────────

def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="FinanceFlow-AI",
        description="FP&A variance analysis: load files, compute variances, "
                    "generate AI commentary, and export a three-tab Excel report.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    p.add_argument("--budget",   default=config.BUDGET_PATH,
                   help="Path to budget Excel/CSV file")
    p.add_argument("--actuals",  default=config.ACTUALS_PATH,
                   help="Path to actuals Excel/CSV file")
    p.add_argument("--drivers",  default=config.DRIVERS_PATH,
                   help="Path to drivers CSV file")
    p.add_argument("--no-drivers", action="store_true",
                   help="Skip the drivers file (commentary will note missing drivers)")
    p.add_argument("--output",   default=None,
                   help="Output Excel path (default: output/FinanceFlow_Variance_Report.xlsx)")
    p.add_argument("--materiality-dollars", type=float,
                   default=config.MATERIALITY_THRESHOLD_DOLLARS,
                   help="Absolute dollar threshold for material variances")
    p.add_argument("--materiality-pct", type=float,
                   default=config.MATERIALITY_THRESHOLD_PERCENT,
                   help="Percent-of-budget threshold for material variances")
    return p


def main():
    parser  = _build_parser()
    args    = parser.parse_args()

    drivers = None if args.no_drivers else args.drivers

    print()
    print("=" * 58)
    print("  FinanceFlow-AI  |  FP&A Variance Analysis")
    print("=" * 58)
    print(f"  Budget:   {args.budget}")
    print(f"  Actuals:  {args.actuals}")
    print(f"  Drivers:  {'(none)' if drivers is None else drivers}")
    print(f"  Material: ${args.materiality_dollars:,.0f} or "
          f"{args.materiality_pct:.1f}% of budget")
    print()

    try:
        run_pipeline(
            budget_path  = args.budget,
            actuals_path = args.actuals,
            drivers_path = drivers,
            output_path  = args.output,
            mat_dollars  = args.materiality_dollars,
            mat_pct      = args.materiality_pct,
        )
    except (FileNotFoundError, ValueError) as e:
        print(f"\n  ERROR: {e}\n", file=sys.stderr)
        sys.exit(1)


# ── Print helpers ─────────────────────────────────────────────────────────────

def _print_step(n: int, label: str):
    print(f"\n  Step {n}: {label}...")

def _print_done(t0: float):
    print(f"  Done ({time.time() - t0:.1f}s)")

def _print_summary_line(label: str, value):
    print(f"  {label + ':':<32} {value}")


if __name__ == "__main__":
    main()
