"""scorecard.py - compare every model you have tested, side by side.

Usage (from the ai-engineer-lab folder):
    python evals/scorecard.py          # prints the table and writes evals/scorecard.md
"""
import json
from pathlib import Path
from statistics import mean

EVALS = Path(__file__).resolve().parent
TYPES = ["easy", "cross-plan", "multi-doc", "math", "trap"]


def pct(values) -> str:
    values = list(values)
    return f"{100 * mean(values):.0f}%" if values else "-"


def summarize(result: dict) -> dict:
    runs = result["runs"]
    qa = [g for r in runs for g in r.get("qa", [])]
    claims = [g for r in runs for g in r.get("claims", [])]
    row = {"Model": result["model_name"], "Runs": str(len(runs))}
    row["Questions"] = pct(g["passed"] for g in qa)
    for t in TYPES:
        row[t] = pct(g["passed"] for g in qa if g["type"] == t)
    row["Claims"] = pct(g["passed"] for g in claims)

    # Consistency: questions/claims where the runs did not all agree
    flips = 0
    for part in ("qa", "claims"):
        by_id = {}
        for r in runs:
            for g in r.get(part, []):
                by_id.setdefault(g["id"], set()).add(g["passed"])
        flips += sum(len(v) > 1 for v in by_id.values())
    row["Flip-flops"] = str(flips) if len(runs) > 1 else "-"

    row["Sec/question"] = f"{mean(g['seconds'] for g in qa):.1f}" if qa else "-"
    row["Sec/claim"] = f"{mean(g['seconds'] for g in claims):.1f}" if claims else "-"
    cost = mean(r["cost_usd"] for r in runs)
    row["Cost/run"] = f"${cost:.2f}" if result["model"] == "claude" else "$0 (local)"
    row["_search"] = pct(g["search_found_sources"] for g in qa if g["type"] != "trap")
    return row


def failures(result: dict) -> list[str]:
    lines = []
    for r in result["runs"]:
        for g in r.get("qa", []):
            if not g["passed"]:
                why = f"missing {g['missing']}" if g["missing"] else "did not say I don't know"
                lines.append(f"- run {r['run']} {g['id']} ({g['type']}): {why}")
        for g in r.get("claims", []):
            if not g["passed"]:
                lines.append(f"- run {r['run']} {g['id']}: said {g['got']}, key says {g['want']}")
    return lines


if __name__ == "__main__":
    results = [json.loads(p.read_text()) for p in sorted((EVALS / "results").glob("*.json"))]
    if not results:
        raise SystemExit("No results yet. Run: python evals/run_evals.py --model small")
    rows = [summarize(r) for r in results]
    cols = [c for c in rows[0] if not c.startswith("_")]

    table = ["| " + " | ".join(cols) + " |", "|" + "---|" * len(cols)]
    table += ["| " + " | ".join(row[c] for c in cols) + " |" for row in rows]
    md = ["# Lakeside AI scorecard", "", *table, "",
          f"Search found the right doc(s) for {rows[0]['_search']} of answerable questions "
          "(same search for every model, so a miss here is a search problem, not a model problem).", ""]
    for r in results:
        md += [f"## What {r['model_name']} got wrong", *(failures(r) or ["- nothing"]), ""]

    print("\n".join(md))
    (EVALS / "scorecard.md").write_text("\n".join(md), encoding="utf-8")
    print("Wrote evals/scorecard.md")
