"""
commentary.py — AI-generated variance commentary with template fallback.

WHAT IT DOES (in finance terms):
  This is the module that replaces the 3 hours of writing every analyst
  dreads at month-end. It produces two outputs:

    1. LINE COMMENTARY — one sentence per material variance explaining
       what happened and why. Goes into the Excel report and the dashboard
       next to each flagged line item.

    2. EXECUTIVE SUMMARY — three CFO-ready bullet points summarizing the
       biggest stories in the period: revenue, costs, and any bright spots.
       Goes on the front page of the report.

WHY THE HALLUCINATION CONTROLS MATTER:
  A naive AI prompt would be: "Here's our budget vs actuals, write commentary."
  The AI would then invent plausible-sounding reasons for every variance —
  seasonal patterns, economic conditions, headcount changes — none of which
  may be true. That's worse than no commentary at all, because it gives the
  CFO false confidence in explanations that budget owners never confirmed.

  The control: the AI is ONLY allowed to use numbers the variance engine
  computed and causes that came directly from the drivers file. If no driver
  note exists for a line item, the AI says exactly one thing:
  "Driver pending budget owner input." — so the analyst knows who to chase.

FALLBACK DESIGN:
  If no API key is set (or the API call fails for any reason), the module
  falls back to deterministic template commentary. The pipeline always
  completes. An analyst without an API key still gets a complete, usable
  report — just with fill-in-the-blank sentences instead of natural language.
"""

import os
from dotenv import load_dotenv
import pandas as pd
from src.config import CLAUDE_MODEL, MAX_TOKENS

load_dotenv()  # reads .env file if present


# ── Detect whether AI is available ────────────────────────────────────────────

def _ai_available() -> bool:
    """Return True if anthropic is importable and an API key is set."""
    try:
        import anthropic  # noqa: F401
        return bool(os.getenv("ANTHROPIC_API_KEY"))
    except ImportError:
        return False


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_commentary(results: dict, data: dict) -> dict:
    """
    Takes the variance engine results and returns a dict with:
      "line_commentary"   — dict keyed by (Month, Department, Line Item)
                            → one-sentence string
      "executive_summary" — list of 3 bullet-point strings for the CFO
      "ai_used"           — bool: True if Claude API was called, False if templates
    """
    drivers = data["drivers"]
    monthly = results["monthly"]
    material_rows = monthly[monthly["Material"]].copy()

    if _ai_available():
        line_commentary   = _ai_line_commentary(material_rows, drivers)
        executive_summary = _ai_executive_summary(results["pl_summary"],
                                                   results["ytd"], drivers)
        ai_used = True
    else:
        print("[COMMENTARY] No API key found — using template commentary.")
        line_commentary   = _template_line_commentary(material_rows, drivers)
        executive_summary = _template_executive_summary(results["pl_summary"],
                                                        results["ytd"], drivers)
        ai_used = False

    return {
        "line_commentary":   line_commentary,
        "executive_summary": executive_summary,
        "ai_used":           ai_used,
    }


# ── AI commentary ─────────────────────────────────────────────────────────────

def _ai_line_commentary(material_rows: pd.DataFrame, drivers: pd.DataFrame) -> dict:
    """
    Call Claude once per material line item to produce one sentence of commentary.

    PROMPT DESIGN DECISIONS:
      1. We pass only the computed numbers — not raw data.  The AI cannot
         hallucinate a number because we give it the number.
      2. We pass only the driver note from the drivers file as the allowed
         cause.  The system prompt explicitly forbids adding any cause not
         in the driver note.
      3. We cap output at 40 words.  Finance commentary belongs in cells,
         not paragraphs.  A 400-word AI essay is not useful in an Excel report.
      4. If there is no driver note, we tell the AI exactly what to say.
         It does not get to improvise.

    INTERVIEW ANGLE:
      "How do you prevent the AI from making things up?"
      Answer: two constraints — scope (it only sees computed numbers, not raw
      files) and attribution (it can only explain a variance using text that
      came from a budget owner, not from its training data).
    """
    import anthropic
    client = anthropic.Anthropic()
    commentary = {}

    for _, row in material_rows.iterrows():
        key = (row["Month"], row["Department"], row["Line Item"])
        driver_note = _lookup_driver(row, drivers)

        if not driver_note:
            commentary[key] = "Driver pending budget owner input."
            continue

        prompt = f"""You are writing one sentence of variance commentary for a CFO report.

DATA (do not alter these numbers):
  Period:      {row['Month']}
  Department:  {row['Department']}
  Line Item:   {row['Line Item']}
  Category:    {row['Category']}
  Budget:      ${row['Amount_budget']:,.0f}
  Actual:      ${row['Amount_actual']:,.0f}
  Variance:    ${row['Variance $']:+,.0f}  ({row['Variance %']:+.1f}% vs budget)
  Direction:   {row['F/U']}

APPROVED DRIVER NOTE (this is the ONLY cause you may reference):
  "{driver_note}"

RULES:
  - Write exactly ONE sentence, maximum 35 words.
  - Mention the dollar variance and direction (above/below budget).
  - Attribute the cause ONLY to the driver note. Do not add context,
    assumptions, or any information not in the driver note above.
  - Do not use the word "significant" or "notable".
  - Output only the sentence, no preamble, no label."""

        try:
            response = client.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=100,
                messages=[{"role": "user", "content": prompt}],
            )
            commentary[key] = response.content[0].text.strip()
        except Exception as e:
            # If one call fails, fall back to template for that line item only.
            print(f"[COMMENTARY] API call failed for {key}: {e}")
            commentary[key] = _template_sentence(row, driver_note)

    return commentary


def _ai_executive_summary(pl_summary: pd.DataFrame, ytd: pd.DataFrame,
                           drivers: pd.DataFrame) -> list:
    """
    Call Claude once to produce a 3-bullet executive summary for the CFO.

    WHAT GOES INTO THE PROMPT:
      - The P&L summary (5 rows: Revenue, COGS, GP, Opex, OI)
      - The top 5 YTD variances by net impact (biggest stories)
      - All available driver notes (the only allowed causes)

    WHAT STAYS OUT:
      - Raw transaction data
      - Individual monthly rows
      - Anything not in the variance engine output

    WHY 3 BULLETS:
      CFOs read the executive summary in 30 seconds. Three bullets forces
      prioritization: revenue story, cost story, any bright spot. More than
      three and the analyst is offloading thinking onto the reader.
    """
    import anthropic
    client = anthropic.Anthropic()

    # Build a text summary of the P&L
    pl_text = "\n".join(
        f"  {row['Line']}: Budget ${row['Budget']:,.0f} | "
        f"Actual ${row['Actual']:,.0f} | "
        f"Variance ${row['Variance $']:+,.0f} ({row['Variance %']:+.1f}%) — {row['F/U']}"
        for _, row in pl_summary.iterrows()
    )

    # Top 5 YTD variances by net impact (worst first)
    top5 = ytd.sort_values("YTD_NetImp").head(5)
    top5_text = "\n".join(
        f"  {row['Line Item']} ({row['Department']}): "
        f"YTD variance ${row['YTD_Var']:+,.0f} ({row['YTD_Var_Pct']:+.1f}%) — {row['YTD_FU']}"
        for _, row in top5.iterrows()
    )

    # All driver notes
    if drivers.empty:
        drivers_text = "  No driver notes on file."
    else:
        drivers_text = "\n".join(
            f"  {row['Month']} | {row['Department']} | {row['Line Item']}: {row['Driver Note']}"
            for _, row in drivers.iterrows()
        )

    prompt = f"""You are writing a 3-bullet executive summary for a CFO variance report.

P&L SUMMARY (YTD actuals vs budget):
{pl_text}

TOP 5 YTD VARIANCES (by impact on Operating Income, worst first):
{top5_text}

APPROVED DRIVER NOTES (these are the ONLY causes you may reference):
{drivers_text}

RULES:
  - Write exactly 3 bullet points, each 1-2 sentences.
  - Each bullet must reference specific dollar amounts from the data above.
  - Attribute causes ONLY to the driver notes. Do not invent causes.
  - If a major variance has no driver note, say "driver pending budget owner input."
  - Write for a CFO: plain business English, no jargon, no filler.
  - Format: start each bullet with a bullet point character (•).
  - Output only the 3 bullets, no preamble, no labels."""

    try:
        response = client.messages.create(
            model=CLAUDE_MODEL,
            max_tokens=MAX_TOKENS,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text.strip()
        bullets = [line.strip().lstrip("•").strip()
                   for line in text.split("\n") if line.strip().startswith("•")]
        # If parsing fails, return the whole response as one bullet
        if not bullets:
            bullets = [text]
        return bullets[:3]
    except Exception as e:
        print(f"[COMMENTARY] Executive summary API call failed: {e}")
        return _template_executive_summary(pl_summary, ytd, drivers)


# ── Template fallback ─────────────────────────────────────────────────────────

def _template_line_commentary(material_rows: pd.DataFrame,
                               drivers: pd.DataFrame) -> dict:
    """
    Deterministic one-sentence commentary for every material line item.
    No AI, no API key needed.  Always works.
    """
    commentary = {}
    for _, row in material_rows.iterrows():
        key = (row["Month"], row["Department"], row["Line Item"])
        driver_note = _lookup_driver(row, drivers)
        commentary[key] = _template_sentence(row, driver_note)
    return commentary


def _template_sentence(row: pd.Series, driver_note: str | None) -> str:
    """Build one deterministic sentence from variance data and an optional driver note."""
    direction = "above" if row["Variance $"] > 0 else "below"
    amt = abs(row["Variance $"])
    pct = abs(row["Variance %"])
    fu  = row["F/U"].lower()

    base = (
        f"{row['Line Item']} came in ${amt:,.0f} ({pct:.1f}%) "
        f"{direction} budget in {row['Month']} — {fu}."
    )

    if driver_note:
        return f"{base} {driver_note}"
    else:
        return f"{base} Driver pending budget owner input."


def _template_executive_summary(pl_summary: pd.DataFrame, ytd: pd.DataFrame,
                                 drivers: pd.DataFrame) -> list:
    """
    Three deterministic bullet points built from P&L summary rows.
    Covers: (1) revenue, (2) biggest cost driver, (3) operating income.
    """
    def pl_row(line_name):
        rows = pl_summary[pl_summary["Line"] == line_name]
        return rows.iloc[0] if not rows.empty else None

    rev = pl_row("Revenue")
    opex = pl_row("Opex")
    oi  = pl_row("Operating Income")

    # Bullet 1: Revenue
    if rev is not None:
        rev_dir = "below" if rev["Variance $"] < 0 else "above"
        b1 = (f"YTD revenue of ${rev['Actual']:,.0f} is "
              f"${abs(rev['Variance $']):,.0f} ({abs(rev['Variance %']):.1f}%) "
              f"{rev_dir} budget — {rev['F/U'].lower()}.")
    else:
        b1 = "Revenue data unavailable."

    # Bullet 2: Biggest cost driver from YTD
    cost_ytd = ytd[ytd["Category"].isin(["COGS", "Opex"])].sort_values("YTD_NetImp")
    if not cost_ytd.empty:
        top_cost = cost_ytd.iloc[0]
        cost_dir = "above" if top_cost["YTD_Var"] > 0 else "below"
        driver_match = drivers[
            (drivers["Department"] == top_cost["Department"]) &
            (drivers["Line Item"]  == top_cost["Line Item"])
        ] if not drivers.empty else pd.DataFrame()
        driver_text = (f" {driver_match.iloc[0]['Driver Note']}"
                       if not driver_match.empty else
                       " Driver pending budget owner input.")
        b2 = (f"Largest cost driver: {top_cost['Line Item']} "
              f"({top_cost['Department']}) is ${abs(top_cost['YTD_Var']):,.0f} "
              f"({abs(top_cost['YTD_Var_Pct']):.1f}%) {cost_dir} budget YTD.{driver_text}")
    else:
        b2 = "Cost data unavailable."

    # Bullet 3: Operating income
    if oi is not None:
        oi_dir = "below" if oi["Variance $"] < 0 else "above"
        b3 = (f"YTD operating income of ${oi['Actual']:,.0f} is "
              f"${abs(oi['Variance $']):,.0f} ({abs(oi['Variance %']):.1f}%) "
              f"{oi_dir} budget — {oi['F/U'].lower()}.")
    else:
        b3 = "Operating income data unavailable."

    return [b1, b2, b3]


# ── Shared helper ─────────────────────────────────────────────────────────────

def _lookup_driver(row: pd.Series, drivers: pd.DataFrame) -> str | None:
    """
    Find the driver note for a given Month + Department + Line Item.
    Returns the note string, or None if no match.

    WHY WE LOOK UP BY THREE KEYS:
      A driver note is specific to a time period, a department, and a line
      item. Engineering Salaries in March has a different cause than
      Engineering Salaries in April. Matching on all three prevents the
      wrong explanation from appearing under the wrong month.
    """
    if drivers.empty:
        return None
    match = drivers[
        (drivers["Month"]      == row["Month"]) &
        (drivers["Department"] == row["Department"]) &
        (drivers["Line Item"]  == row["Line Item"])
    ]
    if match.empty:
        return None
    return match.iloc[0]["Driver Note"]
