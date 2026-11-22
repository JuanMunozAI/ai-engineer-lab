"""ask.py - answer a question from the office docs, with citations.

Usage:
    python ask.py "How many cleanings does SunCoast cover?"                  # local 8B
    python ask.py "How many cleanings does SunCoast cover?" --model big      # local 27B
    python ask.py "How many cleanings does SunCoast cover?" --model claude   # Claude
"""
import argparse
import re
import time

from ingest import search
from llm import MODELS, ask

PROMPT = """You are the front-desk assistant for Lakeside Family Dental.
Answer the question using ONLY the sources below.
After each fact, cite the source number in brackets, like [1].
If the sources don't contain the answer, say "I don't know, please check with the office manager."

Sources:
{sources}

Question: {question}
Answer:"""


def answer(question: str, model: str = "small", k: int = 4) -> tuple[str, list[dict]]:
    hits = search(question, k=k)                       # 1. find the best cards
    sources = "\n\n".join(f"[{i}] ({h['source']})\n{h['text']}" for i, h in enumerate(hits, 1))
    reply = ask(PROMPT.format(sources=sources, question=question), model)   # 2. let the model read them
    reply = re.sub(r"<think>.*?</think>", "", reply, flags=re.S).strip()   # hide qwen's scratch notes
    return reply, hits


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("question")
    parser.add_argument("--model", choices=MODELS, default="small")
    args = parser.parse_args()
    start = time.perf_counter()
    reply, hits = answer(args.question, args.model)
    print(reply)
    print("\nSources:")
    for i, h in enumerate(hits, 1):
        print(f"  [{i}] {h['source']} > {h['section']}")
    print(f"\n[{MODELS[args.model]} - {time.perf_counter() - start:.1f}s]")
