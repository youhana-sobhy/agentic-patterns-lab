# 01 · Basic RAG from scratch

> The whole RAG loop in one file and no extra libraries, so every step is visible.

## ⚙️ Pipeline

| Step | Function | What happens |
|------|----------|--------------|
| 1. Load | `load_documents()` | Read every `.txt` file in [`data/`](data/) |
| 2. Chunk | `chunk_document()` | Split each document into paragraphs: 3 documents → 12 chunks |
| 3. Retrieve | `retrieve()` | Score each chunk by the question words it contains (stopwords removed), keep the top 3 |
| 4. Generate | `answer()` | Send Claude only those chunks; it must answer from them and cite sources like `[nat.txt#1]` |

## 🧪 Test questions

| Question | Retrieved | Expected behavior |
|----------|-----------|-------------------|
| How can many devices share one public IP address? | `nat.txt` paragraphs | Answers from the NAT document, with citations |
| What does the TTL value do in DNS? | `dns.txt` paragraphs | Answers from the DNS document, with citations |
| What is the capital of France? | nothing | Says "I don't know" **without calling the API** |

## 💡 Design decisions

- **No libraries for retrieval.** Keyword overlap is crude, but I can read exactly why each chunk was picked.
- **Strict grounding prompt.** "Answer using ONLY the context" plus a fixed fallback sentence keeps the model from filling gaps from memory.
- **Citations by chunk id.** Every fact points back to `file#paragraph`, so answers are easy to verify.
- **No context, no call.** If retrieval finds nothing, the script returns the fallback directly and saves the request.

## 🔜 Next experiments

- Replace keyword scoring with embeddings (done in [lab 02](../02-semantic-chroma-rag/)).
- Try fixed-size chunks with overlap, and compare the answers.
