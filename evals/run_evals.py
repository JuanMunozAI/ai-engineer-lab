"""run_evals.py - give one model the whole test and save its answers and grades.

Usage (from the ai-engineer-lab folder):
    python evals/run_evals.py --model small                 # 8B: 50 questions + 20 claims, 3 times
    python evals/run_evals.py --model big --runs 1          # 27B, just one pass (faster)
    python evals/run_evals.py --model claude --part qa      # Claude, questions only
    python evals/run_evals.py --model small --limit 5       # quick smoke test: first 5 questions/claims
    python evals/run_evals.py --model small --part qa --k 6 --tag k6   # try 6 cards instead of 4
    python evals/run_evals.py --model small --tag v2        # save as results/small-v2.json, keep the old one

Then:  python evals/scorecard.py   to compare every model you have run.
"""
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
os.chdir(ROOT)                        # data/, docs/ and chroma_db/ live in the project folder
sys.path.insert(0, str(ROOT))

import agent                          # noqa: E402  (Project 2: the claims checker)
from ask import answer                # noqa: E402  (Project 1: the office-manual assistant)
from llm import MODELS, USAGE         # noqa: E402

EVALS = ROOT / "evals"
RESULTS = EVALS / "results"
PRICE_IN, PRICE_OUT = 4.00, 20.00     # Claude Opus 5.5, dollars per million tokens


# ---------- 1. The grader: plain code, no AI ----------

def normalize(text: str) -> str:
    """Make answers easy to compare: lower case, no bold stars, '$1,500' -> '$1500'."""
    text = text.lower().replace("*", "").replace("’", "'")
    text = re.sub(r"(\d),(\d)", r"\1\2", text)
    return re.sub(r"\s+", " ", text)


def has_fact(fact: str, text: str) -> bool:
    """A fact like '6 months|six months' counts if ANY of its spellings is in the answer."""
    return any(normalize(option) in text for option in fact.split("|"))


def said_idk(text: str) -> bool:
    return "don't know" in text or "do not know" in text


def grade_question(q: dict, reply: str, hits: list[dict]) -> dict:
    text = normalize(reply)
    found = [f for f in q["must_include"] if has_fact(f, text)]
    idk = said_idk(text)
    if q.get("idk"):
        passed = idk                                  # trap: the only right answer is "I don't know"
    else:
        passed = len(found) == len(q["must_include"])
    got_sources = {h["source"] for h in hits}
    return {
        "id": q["id"], "type": q["type"], "passed": passed,
        "missing": [f for f in q["must_include"] if f not in found],
        "said_idk": idk,
        "cited": bool(re.search(r"\[\d+\]", reply)),
        "search_found_sources": all(s in got_sources for s in q["sources"]),
        "answer": reply,
    }


# ---------- 2. The test runs ----------

def run_questions(model: str, questions: list[dict], k: int = 4) -> list[dict]:
    graded = []
    for q in questions:
        start = time.perf_counter()
        try:
            reply, hits = answer(q["question"], model, k=k)
        except Exception as e:                        # one broken answer should not stop the test
            reply, hits = f"[error: {e}]", []
        g = grade_question(q, reply, hits)
        g["seconds"] = round(time.perf_counter() - start, 1)
        graded.append(g)
        mark = "OK " if g["passed"] else "XX "
        extra = "" if g["passed"] else (f"  missing: {g['missing']}" if g["missing"] else "  (didn't say I don't know)")
        print(f"  {mark}{q['id']} [{q['type']:10}] {g['seconds']:5.1f}s{extra}")
    return graded


def run_claims(model: str, claim_ids: list[str]) -> list[dict]:
    key = json.loads((ROOT / "data" / "answer_key.json").read_text())
    graded = []
    for cid in claim_ids:
        start = time.perf_counter()
        try:
            text, tools = agent.check(cid, model, verbose=False)
        except Exception as e:
            text, tools = f"[error: {e}]", 0
        got, want = agent.verdict_of(text), key[cid]["verdict"]
        g = {"id": cid, "passed": got == want, "got": got, "want": want, "tool_calls": tools,
             "seconds": round(time.perf_counter() - start, 1), "last_line": text.strip().splitlines()[-1] if text.strip() else ""}
        graded.append(g)
        print(f"  {'OK ' if g['passed'] else 'XX '}{cid}: agent={got:8} key={want:8} {g['seconds']:5.1f}s")
    return graded


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", choices=MODELS, required=True)
    parser.add_argument("--runs", type=int, default=3, help="how many times to take the whole test")
    parser.add_argument("--part", choices=["qa", "claims", "all"], default="all")
    parser.add_argument("--limit", type=int, help="only the first N questions and claims (for a quick try)")
    parser.add_argument("--k", type=int, default=4, help="how many cards search hands the model")
    parser.add_argument("--tag", default="", help="a label for this try, e.g. v2, so old results are kept")
    args = parser.parse_args()

    questions = json.loads((EVALS / "questions.json").read_text())[: args.limit]
    claim_ids = list(agent.CLAIMS)[: args.limit]

    runs = []
    for r in range(1, args.runs + 1):
        USAGE["input"] = USAGE["output"] = 0
        run = {"run": r}
        if args.part in ("qa", "all"):
            print(f"\n[{MODELS[args.model]}] run {r}/{args.runs}: {len(questions)} questions")
            run["qa"] = run_questions(args.model, questions, args.k)
            right = sum(g["passed"] for g in run["qa"])
            print(f"  Questions: {right}/{len(questions)}")
        if args.part in ("claims", "all"):
            print(f"\n[{MODELS[args.model]}] run {r}/{args.runs}: {len(claim_ids)} claims")
            run["claims"] = run_claims(args.model, claim_ids)
            right = sum(g["passed"] for g in run["claims"])
            print(f"  Claims: {right}/{len(claim_ids)}")
        run["tokens"] = dict(USAGE)
        run["cost_usd"] = round(USAGE["input"] / 1e6 * PRICE_IN + USAGE["output"] / 1e6 * PRICE_OUT, 4)
        if args.model == "claude":
            print(f"  Claude cost this run: ${run['cost_usd']:.2f}")
        runs.append(run)

    RESULTS.mkdir(exist_ok=True)
    name = f"{args.model}-{args.tag}" if args.tag else args.model
    out = RESULTS / f"{name}.json"
    label = f"{MODELS[args.model]} {args.tag}".strip()
    out.write_text(json.dumps({"model": args.model, "model_name": label, "part": args.part,
                               "limit": args.limit, "runs": runs}, indent=2))
    print(f"\nSaved {out.relative_to(ROOT)}. Next: python evals/scorecard.py")
