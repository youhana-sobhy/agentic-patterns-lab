"""Semantic RAG over an infrastructure troubleshooting knowledge base, using ChromaDB.

Flow:
    1. INDEX     store short runbook entries in Chroma; it embeds each one into a vector
    2. SEARCH    embed the question and find the closest entries by vector distance
    3. FILTER    optionally narrow by metadata (for example tool="aws"), and drop
                 anything farther than MAX_DISTANCE so unrelated questions return nothing
    4. GENERATE  give Claude only the matching entries and ask for a grounded fix

Unlike 01-basic-rag, matching is by meaning, not shared words:
"my virtual machine is lagging" finds "VMware VM is very slow".

Run:
    python 02-augmented-llm/rag/02-semantic-chroma-rag/rag.py
"""

import os
import sys

import chromadb
from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads ANTHROPIC_API_KEY from the nearest .env file

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env at the repo root and add your key.")

MODEL = "claude-sonnet-5-5"
TOP_K = 2

# Chroma's default distance is squared L2 between normalized vectors (0 = identical).
# From my test runs: relevant matches scored about 0.7-1.5, unrelated ones about 1.9+.
MAX_DISTANCE = 1.5

# ---------------------------------------------------------------
# Knowledge base: (text, tool) pairs kept together so they can't get out of sync
# ---------------------------------------------------------------

KNOWLEDGE_BASE = [
    ("Ansible playbook fails with UNREACHABLE because the SSH key is missing or the host is not in the inventory", "ansible"),
    ("Ansible task hangs forever because of a sudo password prompt, set become_pass or use passwordless sudo", "ansible"),
    ("Ansible YAML syntax error caused by wrong indentation in the playbook", "ansible"),
    ("APIC tenant creation returns 400 because a VRF with the same name already exists", "aci"),
    ("APIC API login returns 401 because the token expired, re-authenticate with aaaLogin", "aci"),
    ("ACI contract is not allowing traffic because the EPG is missing the provider or consumer relation", "aci"),
    ("EC2 instance is out of disk space, extend the EBS volume and then grow the filesystem", "aws"),
    ("AWS Lambda times out because the function is in a VPC without a NAT gateway", "aws"),
    ("S3 access denied error caused by a bucket policy that blocks the IAM role", "aws"),
    ("VMware VM is very slow because the host has CPU ready time and memory ballooning", "vmware"),
    ("VMware vMotion fails because the source and destination hosts have different CPU compatibility", "vmware"),
    ("Terraform apply fails with state lock error because a previous run was interrupted", "terraform"),
]


# ---------------------------------------------------------------
# 1. Index
# ---------------------------------------------------------------

def build_collection() -> chromadb.Collection:
    """Create an in-memory collection and add every entry (Chroma embeds them for us)."""
    collection = chromadb.Client().get_or_create_collection("infra_kb")

    # upsert instead of add: re-running with a persistent client won't create duplicates.
    collection.upsert(
        ids=[f"doc{i}" for i in range(len(KNOWLEDGE_BASE))],
        documents=[text for text, _ in KNOWLEDGE_BASE],
        metadatas=[{"tool": tool} for _, tool in KNOWLEDGE_BASE],
    )
    return collection


def show_embeddings(collection: chromadb.Collection, n: int = 3) -> None:
    """Peek at what Chroma stored: each document became a vector of numbers."""
    data = collection.get(include=["documents", "embeddings"], limit=n)
    dims = len(data["embeddings"][0])
    print(f"Indexed {collection.count()} entries. Each one is a {dims}-dimensional vector, e.g.:")
    for doc_id, doc, vec in zip(data["ids"], data["documents"], data["embeddings"]):
        print(f"  {doc_id}: {doc[:60]}...")
        print(f"         first 5 numbers: {[round(float(x), 3) for x in vec[:5]]}")


# ---------------------------------------------------------------
# 2-3. Search and filter
# ---------------------------------------------------------------

def search(collection: chromadb.Collection, question: str, tool: str | None = None,
           k: int = TOP_K) -> list[dict]:
    """Return the k closest entries within MAX_DISTANCE, optionally limited to one tool."""
    res = collection.query(
        query_texts=[question],
        n_results=k,
        where={"tool": tool} if tool else None,
    )
    hits = [
        {"id": i, "text": d, "tool": m["tool"], "distance": dist}
        for i, d, m, dist in zip(res["ids"][0], res["documents"][0],
                                 res["metadatas"][0], res["distances"][0])
    ]
    return [h for h in hits if h["distance"] <= MAX_DISTANCE]


def print_search(collection: chromadb.Collection, question: str, tool: str | None = None) -> None:
    label = f"{question}  (tool={tool})" if tool else question
    print(f"\nQ: {label}")
    hits = search(collection, question, tool)
    for h in hits:
        print(f"  [{h['distance']:.2f}] {h['text']}")
    if not hits:
        print(f"  (no entry within distance {MAX_DISTANCE})")


# ---------------------------------------------------------------
# 4. Generate
# ---------------------------------------------------------------

def answer(collection: chromadb.Collection, question: str, tool: str | None = None) -> str:
    """Full RAG: retrieve matching entries, then let Claude answer only from them."""
    hits = search(collection, question, tool)
    if not hits:
        # Nothing relevant: skip the API call instead of letting the model guess.
        return "No matching entry in the knowledge base."

    context = "\n".join(f'<entry id="{h["id"]}" tool="{h["tool"]}">{h["text"]}</entry>' for h in hits)
    prompt = f"""You are an infrastructure support assistant.
Using ONLY the knowledge base entries below, give the most likely cause and the fix in 2-3 sentences.
Cite the entry id you used, like [doc7]. If the entries don't fit the problem, say so.

<entries>
{context}
</entries>

<problem>{question}</problem>"""

    response = Anthropic().messages.create(
        model=MODEL,
        max_tokens=300,
        messages=[{"role": "user", "content": prompt}],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


# ---------------------------------------------------------------
# Main
# ---------------------------------------------------------------

if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")

    kb = build_collection()
    show_embeddings(kb)

    print("\n=== Semantic search (lower distance = closer meaning) ===")
    print_search(kb, "I can't login to the server remotely")
    print_search(kb, "my virtual machine is lagging")
    print_search(kb, "can't create a new tenant")
    print_search(kb, "lambda can't reach the internet")
    print_search(kb, "what's the weather today")            # unrelated: should return nothing
    print_search(kb, "connection problem", tool="aws")      # same question, different filter...
    print_search(kb, "connection problem", tool="ansible")  # ...gives different answers

    print("\n=== Full RAG: retrieve, then generate ===")
    for q in ["lambda can't reach the internet", "what's the weather today"]:
        print(f"\nQ: {q}\nA: {answer(kb, q)}")
