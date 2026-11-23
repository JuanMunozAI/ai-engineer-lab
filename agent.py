"""agent.py - an AI billing assistant that checks insurance claims using tools.

Usage:
    python agent.py C04                    # check one claim with Claude, watch every tool call
    python agent.py C04 --model big        # same, with the local 27B through Ollama
    python agent.py --all                  # check all 20 claims and grade against the answer key
    python agent.py --all --model big      # grade the local 27B
"""
import argparse
import json
import re
import time
from datetime import date
from pathlib import Path

import anthropic
import ollama

from ingest import search
from llm import MODELS, USAGE

MODEL = "claude-opus-5-5"
DATA = Path("data")
CLAIMS = {c["claim_id"]: c for c in json.loads((DATA / "claims.json").read_text())}
PATIENTS = {p["patient_id"]: p for p in json.loads((DATA / "patients.json").read_text())}

SYSTEM = """You are the insurance billing checker at Lakeside Family Dental (a fictional practice).
Your job: before a claim is sent, find anything that would get it rejected or is against office policy.

Use the tools. Always pull the claim and the patient, and look up the rules in the office manual
instead of relying on memory. Use date_math for any date or age calculation.
Today is 2026-11-22.

Finish with a short explanation, then a last line in exactly this form:
VERDICT: OK
or
VERDICT: PROBLEM - <one-sentence reason>"""

# ---------- 1. The tools: plain Python functions ----------

def get_claim(claim_id: str) -> dict:
    return CLAIMS.get(claim_id) or {"error": f"No claim {claim_id}"}


def get_patient(patient_id: str) -> dict:
    return PATIENTS.get(patient_id) or {"error": f"No patient {patient_id}"}


def search_office_manual(query: str) -> list[dict]:
    """Reuses Project 1's RAG search."""
    return [{"source": f"{h['source']} > {h['section']}", "text": h["text"]} for h in search(query, k=4)]


def date_math(start: str, end: str) -> dict:
    a, b = date.fromisoformat(start), date.fromisoformat(end)
    months = (b.year - a.year) * 12 + (b.month - a.month) - (b.day < a.day)
    return {"days": (b - a).days, "whole_months": months, "whole_years": months // 12}


# Required fields per code, straight from docs/insurance/13-claim-submission-procedure.md and the CDT notes.
# Plain code, not AI: a checklist that never gets tired or skips a box.
NEEDS_TOOTH = {"D1351", "D2391", "D2392", "D2740", "D2950"}
NEEDS_SURFACE = {"D2391": 1, "D2392": 2}           # code -> number of surfaces it means
NEEDS_QUADRANT = {"D4341", "D4342"}


def check_required_fields(claim_id: str) -> dict:
    claim = CLAIMS.get(claim_id)
    if not claim:
        return {"error": f"No claim {claim_id}"}
    missing = []
    if not claim.get("rendering_provider_npi"):
        missing.append("rendering provider NPI")
    if not claim.get("date_of_service"):
        missing.append("date of service")
    for p in claim["procedures"]:
        code = p["code"]
        if code in NEEDS_TOOTH and not p.get("tooth"):
            missing.append(f"{code}: tooth number")
        if code in NEEDS_SURFACE:
            if not p.get("surface"):
                missing.append(f"{code}: surface")
            elif len(p["surface"]) != NEEDS_SURFACE[code]:
                missing.append(f"{code}: has {len(p['surface'])} surface(s) but this code means {NEEDS_SURFACE[code]}")
        if code in NEEDS_QUADRANT and not p.get("quadrant"):
            missing.append(f"{code}: quadrant")
    return {"claim_id": claim_id, "problems": missing, "all_required_fields_present": not missing}


FUNCTIONS = {f.__name__: f for f in (get_claim, get_patient, search_office_manual, date_math, check_required_fields)}

# ---------- 2. The tool "menu" Claude reads (name, what it does, what to pass in) ----------

TOOLS = [
    {
        "name": "get_claim",
        "description": "Get one insurance claim by its ID, e.g. C04: plan, procedures, fees, attachments, pre-auth.",
        "input_schema": {"type": "object", "properties": {"claim_id": {"type": "string"}},
                         "required": ["claim_id"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "get_patient",
        "description": "Get a patient by ID, e.g. P004: birth date, plan, member-since date, HMO assignment, past visits.",
        "input_schema": {"type": "object", "properties": {"patient_id": {"type": "string"}},
                         "required": ["patient_id"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "search_office_manual",
        "description": "Search the office manual (insurance plan rules, claim procedures, CDT code notes, policies). "
                       "Returns the 4 most relevant sections. Ask specific questions, e.g. 'SunCoast pre-authorization limit'.",
        "input_schema": {"type": "object", "properties": {"query": {"type": "string"}},
                         "required": ["query"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "date_math",
        "description": "Exact time between two dates (YYYY-MM-DD): days, whole months, whole years. "
                       "Use for ages (birth date to service date), time since last cleaning, filing deadlines.",
        "input_schema": {"type": "object",
                         "properties": {"start": {"type": "string"}, "end": {"type": "string"}},
                         "required": ["start", "end"], "additionalProperties": False},
        "strict": True,
    },
    {
        "name": "check_required_fields",
        "description": "Rule check for required claim fields: tooth numbers, filling surfaces (and that the surface "
                       "count matches the code), deep-cleaning quadrants, provider NPI. Run it on every claim.",
        "input_schema": {"type": "object", "properties": {"claim_id": {"type": "string"}},
                         "required": ["claim_id"], "additionalProperties": False},
        "strict": True,
    },
]


def run_tool(name: str, args: dict) -> str:
    try:
        return json.dumps(FUNCTIONS[name](**args))
    except Exception as e:                      # a broken tool call should not crash the agent
        return json.dumps({"error": str(e)})

# ---------- 3. The agent loop: Claude picks a tool, we run it, repeat until it answers ----------

def check_claim(claim_id: str, verbose: bool = True) -> tuple[str, int]:
    client = anthropic.Anthropic()
    messages = [{"role": "user", "content": f"Check claim {claim_id}."}]
    tool_calls = 0
    for _ in range(15):                         # safety limit so it can never loop forever
        resp = client.beta.messages.create(
            model=MODEL, max_tokens=16000, system=SYSTEM, tools=TOOLS, messages=messages,
            output_config={"effort": "medium"},
            betas=["server-side-fallback-2026-07-01"], fallbacks="default",
        )
        USAGE["input"] += resp.usage.input_tokens
        USAGE["output"] += resp.usage.output_tokens
        if resp.stop_reason == "refusal":
            return "VERDICT: PROBLEM - Claude declined to review this claim", tool_calls
        messages.append({"role": "assistant", "content": resp.content})
        uses = [b for b in resp.content if b.type == "tool_use"]
        if not uses:                            # no tool requested = final answer
            return "".join(b.text for b in resp.content if b.type == "text"), tool_calls
        results = []
        for u in uses:
            tool_calls += 1
            if verbose:
                print(f"  -> {u.name}({json.dumps(u.input)})")
            results.append({"type": "tool_result", "tool_use_id": u.id, "content": run_tool(u.name, u.input)})
        messages.append({"role": "user", "content": results})
    return "VERDICT: PROBLEM - agent hit the step limit", tool_calls


# ---------- 3b. The same loop for a local model (Ollama) ----------
# Same tools, same rules, different brain. Ollama wants the menu in a slightly different shape.
OLLAMA_TOOLS = [{"type": "function", "function": {"name": t["name"], "description": t["description"],
                 "parameters": t["input_schema"]}} for t in TOOLS]


def check_claim_local(claim_id: str, model: str, verbose: bool = True) -> tuple[str, int]:
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": f"Check claim {claim_id}."}]
    tool_calls = 0
    for _ in range(15):
        resp = ollama.chat(model=MODELS[model], messages=messages, tools=OLLAMA_TOOLS)
        msg = resp.message
        messages.append(msg)
        if not msg.tool_calls:                  # no tool requested = final answer
            return re.sub(r"<think>.*?</think>", "", msg.content or "", flags=re.S).strip(), tool_calls
        for call in msg.tool_calls:
            tool_calls += 1
            name, call_args = call.function.name, dict(call.function.arguments)
            if verbose:
                print(f"  -> {name}({json.dumps(call_args)})")
            messages.append({"role": "tool", "tool_name": name, "content": run_tool(name, call_args)})
    return "VERDICT: PROBLEM - agent hit the step limit", tool_calls


def check(claim_id: str, model: str, verbose: bool = True) -> tuple[str, int]:
    if model == "claude":
        return check_claim(claim_id, verbose)
    return check_claim_local(claim_id, model, verbose)


def verdict_of(text: str) -> str:
    last = [l for l in text.strip().splitlines() if l.strip().upper().startswith("VERDICT")]
    return "PROBLEM" if last and "PROBLEM" in last[-1].upper() else ("OK" if last else "UNKNOWN")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("claim_id", nargs="?", help="e.g. C04")
    parser.add_argument("--all", action="store_true", help="check every claim and grade the results")
    parser.add_argument("--model", choices=MODELS, default="claude", help="claude, big (27B) or small (8B)")
    args = parser.parse_args()

    if args.all:
        key = json.loads((DATA / "answer_key.json").read_text())
        right = 0
        for cid in CLAIMS:
            start = time.perf_counter()
            text, n = check(cid, args.model, verbose=False)
            got, want = verdict_of(text), key[cid]["verdict"]
            right += got == want
            mark = "OK " if got == want else "XX "
            print(f"{mark}{cid}: agent={got:8} key={want:8} tools={n:2} {time.perf_counter() - start:5.1f}s")
            if got != want:
                print(f"     agent said: {text.strip().splitlines()[-1]}")
                print(f"     key says:   {key[cid]['reason']}")
        print(f"\nScore: {right}/{len(CLAIMS)}  [{MODELS[args.model]}]")
    elif args.claim_id:
        start = time.perf_counter()
        text, n = check(args.claim_id.upper(), args.model)
        print("\n" + text)
        print(f"\n[{MODELS[args.model]} - {n} tool calls - {time.perf_counter() - start:.1f}s]")
    else:
        parser.print_help()
