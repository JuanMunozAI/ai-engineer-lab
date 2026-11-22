"""llm.py - send one prompt to a local model (Ollama) or to Claude.

Usage:
    python llm.py "What is a CDT code?"                  # local 8B (default)
    python llm.py "What is a CDT code?" --model big      # local 27B
    python llm.py "What is a CDT code?" --model claude   # Claude API
"""
import argparse
import time

MODELS = {
    "small": "qwen3:8b",         # local, fast
    "big": "qwen3.8:27b",        # local, smarter, fits in 32 GB VRAM
    "claude": "claude-opus-5-5", # frontier model through the API
}


def ask(prompt: str, model: str = "small") -> str:
    """Return the model's answer as plain text."""
    if model == "claude":
        import anthropic  # reads ANTHROPIC_API_KEY from the environment

        client = anthropic.Anthropic()
        resp = client.beta.messages.create(
            model=MODELS["claude"],
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",  # retry on another model if this one declines
        )
        if resp.stop_reason == "refusal":
            return "[Claude declined this request]"
        return "".join(b.text for b in resp.content if b.type == "text")

    import ollama  # talks to the Ollama app on localhost:11434

    resp = ollama.chat(model=MODELS[model], messages=[{"role": "user", "content": prompt}])
    return resp["message"]["content"]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("prompt")
    parser.add_argument("--model", choices=MODELS, default="small")
    args = parser.parse_args()

    start = time.perf_counter()
    answer = ask(args.prompt, args.model)
    print(answer)
    print(f"\n[{MODELS[args.model]} - {time.perf_counter() - start:.1f}s]")
