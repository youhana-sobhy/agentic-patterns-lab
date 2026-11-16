# 02 · Semantic RAG with ChromaDB

> Retrieval by meaning instead of shared words, over an infrastructure troubleshooting knowledge base.

## 🎯 Scenario

A small knowledge base of real-world infrastructure issues: **Ansible, Cisco ACI/APIC, AWS, VMware, Terraform**. Each entry is tagged with its tool. An engineer describes a problem in plain words, and the system finds the matching known issue and suggests the fix.

## ⚙️ Pipeline

| Step | What happens |
|------|--------------|
| 1. Index | Entries are `upsert`-ed into a Chroma collection. Chroma embeds each one into a vector automatically (384 dimensions with its default model). |
| 2. Search | The question is embedded the same way, and Chroma returns the nearest entries by vector distance. |
| 3. Filter | Optional metadata filter (`tool="aws"`), plus a **distance cut-off** (`MAX_DISTANCE = 1.5`) that drops anything too far away. |
| 4. Generate | Claude gets only the surviving entries and gives the likely cause and fix, citing the entry id like `[doc7]`. |

## 📊 Results from my runs

Lower distance means closer meaning:

| Question | Best match | Distance |
|----------|------------|:--------:|
| my virtual machine is lagging | VMware VM is very slow because of CPU ready time and memory ballooning | **0.76** |
| lambda can't reach the internet | AWS Lambda times out because the function is in a VPC without a NAT gateway | **0.76** |
| can't create a new tenant | APIC tenant creation returns 400 because a VRF with the same name exists | **0.89** |
| I can't login to the server remotely | Ansible UNREACHABLE because the SSH key is missing | 1.49 |
| what's the weather today | *(Terraform entry)* | 1.96 → **rejected** |

None of the good matches share key words with the question: "lagging" found "very slow", and "reach the internet" found "NAT gateway". That's the point of embeddings.

## 💡 Design decisions

- **A distance threshold, not just top-k.** Top-k always returns *something*, even for "what's the weather today". I set the cut-off from my measured results: relevant matches scored about 0.7–1.5, unrelated ones about 1.9+.
- **Skip the model when nothing matches.** No relevant entry means no API call and no invented answer.
- **`upsert` instead of `add`.** Re-running with a persistent store won't create duplicates.
- **Text and metadata kept together.** Each entry is a `(text, tool)` pair, so the two lists can never drift out of order.
- **Metadata filters for precision.** The same vague question can be scoped to one tool before ranking.

## 🔎 Open questions I'm exploring

- "connection problem" is too vague: even with a tool filter, nothing lands within 1.5. Should vague questions get a clarifying question back instead of an empty result?
- The 1.5 cut-off fits this small dataset. How should a threshold be tuned on a large, mixed knowledge base?
- Chroma's default distance here is squared L2. Would cosine distance give thresholds that are easier to reason about?
