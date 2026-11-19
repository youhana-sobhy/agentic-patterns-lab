<div align="center">

# 🧪 Agentic Patterns Lab

**A hands-on study of LLM agents, design patterns, and agentic workflows — learned by building.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude%20API-D97757)](https://docs.anthropic.com/)
[![Status](https://img.shields.io/badge/status-actively%20learning-brightgreen)](#-progress)

</div>

---

## 📖 About

This repository is my personal engineering lab for studying how to design and build **agentic systems** with large language models. Each lab isolates a single concept — a pattern, a workflow, or an agent capability — and implements it from first principles using the Claude API, without heavy frameworks, so the mechanics stay visible.

The goal is not just to read about agents, but to **apply** each idea, measure its behavior, and document what I learned along the way.

### Guiding principles

- **Build from scratch** — understand the loop before reaching for a framework.
- **One concept per lab** — small, focused, and runnable on its own.
- **Document the reasoning** — every lab captures *why* the pattern exists and *when* to use it.
- **Simplicity first** — prefer the simplest composition that solves the problem; add autonomy only when it earns its keep.

---

## 🗺️ Curriculum

| # | Module | Focus | Status |
|:-:|--------|-------|:------:|
| 01 | **[Foundations](01-foundations/)** | Prompting, prompt evaluation, structured outputs | 🚧 In progress |
| 02 | **[Augmented LLM](02-augmented-llm/rag/)** | Retrieval (RAG), tool use, memory | 🚧 In progress |
| 03 | **Agent Loops** | Autonomous agents, planning, self-correction | 🔜 Planned |
| 04 | **[Workflows](04-workflows/)** | Composable, predictable LLM pipelines | 🚧 In progress |

### 01 · Foundations: Prompt Evaluation

Treating prompts like code: define success first, build a test set with the messy cases, and grade automatically.

| Lab | Idea | Status |
|-----|------|:------:|
| **[Alert Severity Eval](01-foundations/prompt-evals/alert-severity-eval/)** | Classify monitoring alerts. Exact-match code grading for the label, an LLM grader with a rubric for the explanation, and a check of the grader against hand labels. 15/15 accuracy, 4.40/5 explanations | ✅ |

### 02 · Augmented LLM: RAG

Grounding the model in my own data: retrieve the relevant chunks first, then answer only from them.

| Lab | Idea | Status |
|-----|------|:------:|
| **[Basic RAG](02-augmented-llm/rag/01-basic-rag/)** | Load → chunk → keyword retrieval → grounded answer with citations, no libraries | ✅ |
| **[Semantic RAG with Chroma](02-augmented-llm/rag/02-semantic-chroma-rag/)** | Embeddings, metadata filters, and a distance cut-off over an infrastructure troubleshooting knowledge base | ✅ |
| **Hybrid search + reranking** | Combine keyword and semantic scores | 🔜 |
| **RAG evaluation** | Measure whether answers are grounded in the sources | 🔜 |

### 04 · Workflows

Workflows orchestrate LLMs through predefined code paths — trading some flexibility for predictability and control.

| Pattern | Idea | Lab |
|---------|------|:---:|
| **Prompt Chaining** | Decompose a task into sequential steps, each consuming the previous output | 🔜 |
| **Routing** | Classify the input and dispatch it to a specialized handler | 🔜 |
| **Parallelization** | Run sub-tasks concurrently (sectioning) or sample multiple answers (voting) | 🔜 |
| **Orchestrator–Workers** | A central LLM breaks down work dynamically and delegates to workers | [✅ Lab](04-workflows/Orchestrator-workers/) |
| **Evaluator–Optimizer** | One LLM generates, another critiques, iterating until quality criteria are met | [✅ Lab](04-workflows/evaluator-optimizer/) |

---

## 🏗️ Repository Structure

```text
agentic-patterns-lab/
├── 01-foundations/
│   └── prompt-evals/
│       └── alert-severity-eval/     # success criterion → test set → code + LLM grading
├── 02-augmented-llm/
│   └── rag/
│       ├── 01-basic-rag/            # RAG from scratch: keyword retrieval + citations
│       ├── 02-semantic-chroma-rag/  # embeddings, filters, distance cut-off (ChromaDB)
│       └── README.md                # RAG notes and 01 vs 02 comparison
├── 04-workflows/
│   ├── evaluator-optimizer/
│   │   ├── evaluator_optimizer.py   # generate → check → revise loop
│   │   └── README.md                # lab notes and design decisions
│   └── Orchestrator-workers/
│       ├── orchestrator_workers.py  # plan → parse → parallel workers
│       ├── reference_workflow.py    # reference version I studied, with fixes
│       ├── util.py                  # llm_call + XML parsing helpers
│       └── README.md                # lab notes and debugging log
├── assets/                          # diagrams (PNG + HTML source)
├── .env.example                     # template for your local .env
├── .gitignore
├── requirements.txt
└── README.md
```

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- An [Anthropic API key](https://console.anthropic.com/)

### Setup

```bash
git clone https://github.com/youhana-sobhy/agentic-patterns-lab.git
cd agentic-patterns-lab

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate

pip install -r requirements.txt
```

Copy the template and add your API key. `.env` is git-ignored and must never be committed:

```bash
cp .env.example .env
```

### Run a lab

```bash
python 04-workflows/evaluator-optimizer/evaluator_optimizer.py
```

---

## 📈 Progress

- [x] Repository and lab structure set up
- [x] Prompt evaluation: code grading, an LLM grader with a rubric, and grader validation
- [x] Evaluator–Optimizer workflow
- [x] Orchestrator–Workers workflow
- [ ] Prompt chaining, routing, and parallelization
- [x] RAG: basic keyword RAG and semantic RAG with ChromaDB
- [ ] RAG: hybrid search, reranking, and evaluation
- [ ] Augmented LLM: tool use and memory
- [ ] Autonomous agent loops
- [ ] Evaluation and comparison notes across patterns

---

## 📚 References

- Anthropic — [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Anthropic — [Claude API Documentation](https://docs.anthropic.com/)
- Anthropic — [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)

---

<div align="center">

*Built while learning — one pattern at a time.*

</div>
