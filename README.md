<div align="center">

# 🧪 Agentic Patterns Lab

**A hands-on study of LLM agents, design patterns, and agentic workflows — learned by building.**

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Anthropic](https://img.shields.io/badge/Anthropic-Claude%20API-D97757)](https://docs.anthropic.com/)
[![Status](https://img.shields.io/badge/status-actively%20learning-brightgreen)](#-progress)
[![License](https://img.shields.io/badge/license-MIT-blue)](#-license)

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
| 01 | **Foundations** | Prompting, the Messages API, structured outputs | 🔜 Planned |
| 02 | **Augmented LLM** | Tool use, retrieval, memory | 🔜 Planned |
| 03 | **Agent Loops** | Autonomous agents, planning, self-correction | 🔜 Planned |
| 04 | **[Workflows](04-workflows/)** | Composable, predictable LLM pipelines | 🚧 In progress |

### 04 · Workflows

Workflows orchestrate LLMs through predefined code paths — trading some flexibility for predictability and control.

| Pattern | Idea | Lab |
|---------|------|:---:|
| **Prompt Chaining** | Decompose a task into sequential steps, each consuming the previous output | 🔜 |
| **Routing** | Classify the input and dispatch it to a specialized handler | 🔜 |
| **Parallelization** | Run sub-tasks concurrently (sectioning) or sample multiple answers (voting) | 🔜 |
| **Orchestrator–Workers** | A central LLM breaks down work dynamically and delegates to workers | 🔜 |
| **Evaluator–Optimizer** | One LLM generates, another critiques, iterating until quality criteria are met | [🚧](04-workflows/evaluator-optimizer/) |

---

## 🏗️ Repository Structure

```text
agentic-patterns-lab/
├── 04-workflows/
│   └── evaluator-optimizer/
│       └── evaluator_optimizer.py
├── .gitignore
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

pip install anthropic python-dotenv
```

Create a local `.env` file in the project root with your API key (it is git-ignored and must never be committed):

```bash
ANTHROPIC_API_KEY=your-key-here
```

### Run a lab

```bash
python 04-workflows/evaluator-optimizer/evaluator_optimizer.py
```

---

## 📈 Progress

- [x] Repository and lab structure set up
- [ ] Evaluator–Optimizer workflow
- [ ] Remaining workflow patterns
- [ ] Augmented LLM: tools, retrieval, memory
- [ ] Autonomous agent loops
- [ ] Evaluation and comparison notes across patterns

---

## 📚 References

- Anthropic — [Building Effective Agents](https://www.anthropic.com/engineering/building-effective-agents)
- Anthropic — [Claude API Documentation](https://docs.anthropic.com/)
- Anthropic — [Tool Use Guide](https://docs.anthropic.com/en/docs/build-with-claude/tool-use)

---

## 📄 License

Released under the MIT License.

<div align="center">

*Built while learning — one pattern at a time.*

</div>
