"""Basic RAG (Retrieval-Augmented Generation), built from scratch.

Flow:
    1. LOAD      read the .txt files in data/
    2. CHUNK     split each document into small pieces (paragraphs)
    3. RETRIEVE  score every chunk against the question, keep the top K
    4. GENERATE  give Claude ONLY those chunks and ask it to answer from them

This starter uses simple keyword scoring for retrieval, so it needs no extra
libraries. Swap it for embeddings later (see the TODOs).

Run:
    python 02-augmented-llm/rag/01-basic-rag/basic_rag.py
"""

import os
import re
import sys
from collections import Counter
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads ANTHROPIC_API_KEY from the nearest .env file

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env at the repo root and add your key.")

MODEL = "claude-sonnet-5-5"
DATA_DIR = Path(__file__).parent / "data"
TOP_K = 3

client = Anthropic()

# Common words that would match almost every chunk, so they are ignored when scoring.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "by", "can", "do", "does", "for", "from",
    "how", "in", "is", "it", "its", "of", "on", "or", "so", "that", "the", "their", "they",
    "this", "to", "use", "what", "when", "which", "why", "with", "you", "your",
}


# ---------------------------------------------------------------
# 1. Load
# ---------------------------------------------------------------

def load_documents(folder: Path) -> list[dict]:
    """Return [{"source": file name, "text": file contents}, ...]."""
    return [
        {"source": path.name, "text": path.read_text(encoding="utf-8")}
        for path in sorted(folder.glob("*.txt"))
    ]


# ---------------------------------------------------------------
# 2. Chunk
# ---------------------------------------------------------------

def chunk_document(doc: dict) -> list[dict]:
    """Split a document on blank lines, so each paragraph is one chunk.

    TODO: try fixed-size chunks with overlap (for example 500 characters,
    100 overlap) and compare the answers.
    """
    paragraphs = [p.strip() for p in doc["text"].split("\n\n") if p.strip()]
    return [
        {"source": doc["source"], "chunk_id": i, "text": p}
        for i, p in enumerate(paragraphs)
    ]


# ---------------------------------------------------------------
# 3. Retrieve
# ---------------------------------------------------------------

def tokenize(text: str) -> list[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return [w for w in words if w not in STOPWORDS]


def score(question: str, chunk_text: str) -> int:
    """Count how many question words appear in the chunk.

    TODO: replace with embeddings + cosine similarity, so "IP sharing"
    can match "many devices share one public address" without shared words.
    """
    q_words = set(tokenize(question))
    c_words = Counter(tokenize(chunk_text))
    return sum(c_words[w] for w in q_words)


def retrieve(question: str, chunks: list[dict], k: int = TOP_K) -> list[dict]:
    ranked = sorted(chunks, key=lambda c: score(question, c["text"]), reverse=True)
    return [c for c in ranked[:k] if score(question, c["text"]) > 0]


# ---------------------------------------------------------------
# 4. Generate
# ---------------------------------------------------------------

def build_prompt(question: str, context_chunks: list[dict]) -> str:
    context = "\n\n".join(
        f'<chunk source="{c["source"]}#{c["chunk_id"]}">\n{c["text"]}\n</chunk>'
        for c in context_chunks
    )
    return f"""Answer the question using ONLY the context below.
If the context does not contain the answer, say "I don't know based on the provided documents."
After each fact, cite its source in square brackets, like [nat.txt#1].

<context>
{context}
</context>

<question>{question}</question>"""


def answer(question: str, chunks: list[dict]) -> str:
    context_chunks = retrieve(question, chunks)

    print(f"\nQuestion: {question}")
    print("Retrieved chunks:")
    for c in context_chunks:
        print(f"  - {c['source']}#{c['chunk_id']} (score {score(question, c['text'])})")
    if not context_chunks:
        print("  (none)")
        # Nothing relevant: skip the API call instead of paying for a guaranteed "I don't know".
        return "I don't know based on the provided documents."

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        messages=[{"role": "user", "content": build_prompt(question, context_chunks)}],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    documents = load_documents(DATA_DIR)
    chunks = [chunk for doc in documents for chunk in chunk_document(doc)]
    print(f"Loaded {len(documents)} documents -> {len(chunks)} chunks")

    questions = [
        "How can many devices share one public IP address?",
        "What does the TTL value do in DNS?",
        "What is the capital of France?",  # not in the docs: should say "I don't know"
    ]

    for q in questions:
        print(f"Answer: {answer(q, chunks)}")
        print("-" * 70)
