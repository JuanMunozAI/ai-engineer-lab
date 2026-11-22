"""ingest.py - cut the office docs into chunks and file them in Chroma.

Usage:
    python ingest.py                                   # (re)build the index from docs/
    python ingest.py --search "How many cleanings does SunCoast cover?"
"""
import argparse
from pathlib import Path

import chromadb
import ollama

DOCS_DIR = Path("docs")
DB_DIR = "chroma_db"                 # Chroma saves its files here (git ignores it)
COLLECTION = "office_manual"
EMBED_MODEL = "nomic-embed-text"     # small local model that turns text into numbers


def chunk_markdown(path: Path) -> list[dict]:
    """Split one doc into chunks, one per '## ' section.

    Each chunk starts with the doc title so it still makes sense on its own.
    """
    lines = path.read_text(encoding="utf-8").splitlines()
    title = lines[0].lstrip("# ").strip() if lines else path.stem
    chunks, section, buf = [], "Overview", []

    def flush():
        text = "\n".join(buf).strip()
        if text:
            chunks.append({"text": f"{title}\n{section}\n\n{text}", "section": section})

    for line in lines[1:]:
        if line.startswith("## "):
            flush()
            section, buf = line[3:].strip(), []
        else:
            buf.append(line)
    flush()

    source = path.relative_to(DOCS_DIR).as_posix()
    for i, c in enumerate(chunks):
        c["id"] = f"{source}#{i}"
        c["source"] = source
        c["title"] = title
    return chunks


def embed(texts: list[str]) -> list[list[float]]:
    return ollama.embed(model=EMBED_MODEL, input=texts)["embeddings"]


def get_collection(reset: bool = False):
    client = chromadb.PersistentClient(path=DB_DIR)
    if reset and COLLECTION in [c.name for c in client.list_collections()]:
        client.delete_collection(COLLECTION)   # start fresh so old chunks don't linger
    return client.get_or_create_collection(COLLECTION, metadata={"hnsw:space": "cosine"})


def build_index():
    files = sorted(p for p in DOCS_DIR.rglob("*.md") if p.name != "README.md")
    chunks = [c for f in files for c in chunk_markdown(f)]
    col = get_collection(reset=True)
    col.add(
        ids=[c["id"] for c in chunks],
        documents=[c["text"] for c in chunks],
        embeddings=embed([c["text"] for c in chunks]),
        metadatas=[{"source": c["source"], "title": c["title"], "section": c["section"]} for c in chunks],
    )
    print(f"Indexed {len(chunks)} chunks from {len(files)} docs into {DB_DIR}/")


def search(question: str, k: int = 4) -> list[dict]:
    col = get_collection()
    res = col.query(query_embeddings=embed([question]), n_results=k)
    return [
        {"text": doc, "distance": dist, **meta}
        for doc, dist, meta in zip(res["documents"][0], res["distances"][0], res["metadatas"][0])
    ]


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--search", help="test a question instead of rebuilding")
    args = parser.parse_args()
    if args.search:
        for hit in search(args.search):
            print(f"[{hit['distance']:.3f}] {hit['source']} > {hit['section']}")
    else:
        build_index()
