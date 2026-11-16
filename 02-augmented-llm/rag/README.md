# 📚 RAG: Retrieval-Augmented Generation

> Give the model the right facts at the right moment, so it answers from **your** documents instead of from memory.

An LLM only knows what it was trained on. RAG adds a retrieval step: find the pieces of your own data that match the question, put them in the prompt, and tell the model to answer only from them. That makes the answer **grounded** (you can see where it came from) and **current** (update the documents, not the model).

```text
question ──▶ retrieve relevant chunks ──▶ prompt = question + chunks ──▶ Claude ──▶ grounded answer + sources
```

## 🧪 Labs

I'm building RAG step by step. Each lab changes one thing, so I can see what that change does.

| # | Lab | Retrieval | What it teaches | Status |
|:-:|-----|-----------|-----------------|:------:|
| 01 | [Basic RAG](01-basic-rag/) | Keyword overlap, pure Python | The full RAG loop with no libraries: load → chunk → retrieve → generate, with citations | ✅ |
| 02 | [Semantic RAG with Chroma](02-semantic-chroma-rag/) | Embeddings in ChromaDB | Matching by **meaning**, metadata filters, and a distance cut-off for questions the knowledge base can't answer | ✅ |
| 03 | Better retrieval | Hybrid search + reranking | Combining keyword and semantic scores | 🔜 |
| 04 | RAG evaluation | | Measuring whether answers are grounded in the retrieved sources | 🔜 |

## 🔍 01 vs 02: the same question, two retrievers

I ran lab 01's keyword scorer over lab 02's knowledge base to compare them directly:

| Question | Keyword retrieval (01) | Semantic retrieval (02) |
|----------|------------------------|-------------------------|
| "my virtual machine is lagging" | ❌ Misses: every entry scores 0, since none shares a word with the question | ✅ Finds "VMware VM is very slow" (distance 0.76) |
| "what's the weather today" | Returns nothing, because no words match | ✅ Returns nothing, because everything is past the distance cut-off |

Keyword search is simple and transparent, but it only works when the user happens to use the same words as the document. Embeddings fix that. The trade-off is that you now need a **threshold** to decide when "closest" is still too far away.

## 💡 What I learned so far

- **Retrieval quality limits answer quality.** If the right chunk isn't retrieved, the model can't use it, however good the prompt is.
- **Return nothing rather than something irrelevant.** Both labs skip the model call entirely when nothing relevant is found, instead of paying for a guess.
- **Make the model show its sources.** Asking for citations like `[nat.txt#1]` or `[doc7]` makes every answer checkable.
- **Tune thresholds from real results.** My cut-off of 1.5 comes from measured distances: relevant matches scored about 0.7–1.5 and unrelated ones about 1.9+.
- **Metadata filters are cheap precision.** The same question, "connection problem", should get different answers for AWS and for Ansible. A `where={"tool": ...}` filter handles that before any ranking happens.

## ▶️ Run

From the repository root, after the [setup steps](../../README.md#-getting-started):

```bash
python 02-augmented-llm/rag/01-basic-rag/basic_rag.py
```

```bash
python 02-augmented-llm/rag/02-semantic-chroma-rag/rag.py
```

Lab 02 needs `chromadb` (it's in `requirements.txt`). The first run downloads a small embedding model to your user cache, not into the repo.
