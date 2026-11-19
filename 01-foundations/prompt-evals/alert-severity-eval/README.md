# 🚨 Alert Severity Eval

> An end-to-end prompt evaluation. A prompt reads a raw monitoring alert, labels its severity as `critical`, `warning`, or `info`, and explains why in one sentence. It's measured against a fixed test set with **code grading** for the label and an **LLM grader with a rubric** for the explanation.

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white)
![Claude](https://img.shields.io/badge/Claude-Sonnet%205.5-D97757)
![Result](https://img.shields.io/badge/accuracy-15%2F15-brightgreen)
![Explanations](https://img.shields.io/badge/explanation%20score-4.40%2F5-blue)

## 🎯 Why this lab

Alert triage is a real on-call problem: a wrong `critical` wakes someone up at 3 a.m., and a missed one means an outage nobody's looking at. A prompt that "seems to work" on a few examples isn't good enough. This lab treats the prompt like code: define success first, build a test set that includes the messy cases, grade it automatically, and then check that the grader itself can be trusted.

## 🔁 How it works

```text
            test_cases.json (15 alerts + expected labels)
                              │
                              ▼
            ┌──────────────────────────────────┐
            │  Call 1: Classifier prompt        │
            │  → <severity> + <explanation>     │
            └──────────────────────────────────┘
                 │                         │
         severity│                         │explanation
                 ▼                         ▼
    ┌──────────────────────┐   ┌──────────────────────────────┐
    │ Step 4: Code grading │   │ Step 5: Call 2: LLM grader   │
    │ exact match vs.      │   │ rubric 1–5, reasoning first  │
    │ expected label       │   │ → <reasoning> + <score>      │
    └──────────────────────┘   └──────────────────────────────┘
                 │                         │
                 ▼                         ▼
          accuracy (overall         average score      ──►  Step 6: compare with
          + edge cases)                                      my own hand labels
```

Cases run in parallel (`ThreadPoolExecutor`). Every run writes full results, including explanations and the grader's reasoning, to [`results/latest_run.json`](results/latest_run.json).

## ✅ Step 1: Success criterion

> **The `<severity>` output is exactly one label (`critical`, `warning`, or `info`) that exactly matches the expected label on at least 13 of the 15 test cases (≥ 87% accuracy), including at least 4 of the 5 edge cases.**
>
> Secondary target: explanations average **≥ 4.0 / 5** on the rubric.

Why it's written this way:
- **Specific:** one task, three allowed labels, a fixed output format, so code can grade it.
- **Measurable:** a number on a known test set, not "classifies alerts well".
- **Edge cases counted separately:** a prompt can score high on easy alerts and still fail on the messy ones that matter in production.

The script exits with code `0` when the criterion is met and `1` when it isn't, so it can run as a check in CI.

## 🏷️ Labeling policy

Expected labels follow these rules, so every label in the test set can be defended. The prompt is given the same rules.

| Severity | Meaning | Examples |
|----------|---------|----------|
| `critical` | A production service is down or about to be, data is at risk, or users are affected **now**. Page someone. | Host down, 0 healthy targets, writes failing, fabric node unreachable |
| `warning` | Degraded or trending toward failure, but users aren't affected yet. Act soon, not at 3 a.m. | Disk at 85%, certificate expiring in 14 days, a failed task with no impact |
| `info` | No action needed. | Backup completed, "RESOLVED", Terraform plan shows no changes, test alerts |

**Edge-case rules:**
1. **Content beats the label.** If the alert's own tag (`INFO:`, `CRITICAL:`) contradicts what it describes, classify by what it describes.
2. **Unreadable or empty means `warning`.** Someone still needs to look, because the monitoring integration itself may be broken. But it isn't proof of an outage.
3. **Vague but plausible problems mean `warning`.** Without evidence of impact, don't escalate.

## 🧪 Step 2: Test cases

15 cases in [`test_cases.json`](test_cases.json), covering real infrastructure: Linux hosts, AWS, Cisco ACI, VMware, Terraform, TLS. Each has an `id`, the raw `input`, the `expected` label, an `edge_case` flag, and a `note` justifying the label.

| Expected | Count |
|----------|:-----:|
| `critical` | 4 |
| `warning` | 7 |
| `info` | 4 |
| **Edge cases** (part of the counts above) | **5** |

| id | Edge case | Expected |
|----|-----------|:--------:|
| 10 | Vague: "something looks off with the payments service" | `warning` |
| 11 | Conflicting: tagged `INFO`, but the disk is full and writes are failing | `critical` |
| 12 | Conflicting: tagged `CRITICAL`, but it's a test alert | `info` |
| 13 | Empty input | `warning` |
| 14 | Garbled input | `warning` |

## ✍️ Step 3: The prompt

- **System prompt:** the role (an SRE triaging alerts), the three severity definitions, and the three edge-case rules.
- **User prompt:** the alert inside `<alert>` tags, and a strict output format: `<severity>` and `<explanation>`.

Two lessons from my first version (*"Classify this alert message if critical, warning, or info"*):
- It gave the model **no definitions**, so "critical" meant whatever the model assumed, and the conflicting-tag cases had nothing to go on.
- Free-text output is fragile to grade. XML tags let code pull out exactly the field it needs.

## 🤖 Step 4: Code grading

`code_grade()` passes a case only if the extracted severity is one of the three valid labels **and** matches the expected label exactly. A reply that says `"Critical!"` or explains instead of labeling fails, by design.

## ⚖️ Step 5: LLM grading with a rubric

There's no single right explanation, so `==` can't grade it. A second model call acts as the grader. It sees the alert, the severity and the explanation, and scores the explanation against a **rubric**, a scoring guide that says what each score means:

| Score | Meaning |
|:-----:|---------|
| 5 | One clear sentence that says **what** is wrong, **where**, and **why it matters**, with no unexplained jargon |
| 4 | Clear, but missing one of what / where / why |
| 3 | Understandable but vague |
| 2 | Confusing, too long, or just repeats the alert |
| 1 | Wrong, contradicts the severity, or empty |

Design choices:
- **Reasoning before score.** The grader writes `<reasoning>` first, so the number follows from the judgment rather than the other way round. It also makes disagreements easy to debug.
- **Discrete 1–5 scale** with concrete descriptions, not "rate quality from 1 to 10".
- **Fail closed:** a missing or out-of-range score is recorded as `0` and reported as a grader format error.

## 🔍 Step 6: Validating the grader

The grader is an LLM too, so it can be wrong. To check it, I score 5 explanations by hand with the same rubric, without looking at the grader's scores, in [`human_labels.json`](human_labels.json). The next run prints exact agreement and within-1-point agreement.

**Status:** hand labels pending. The comparison code is in place.

## 📊 Results (latest run)

| Metric | Result | Target |
|--------|:------:|:------:|
| Overall accuracy | **15 / 15 (100%)** | ≥ 13 |
| Edge-case accuracy | **5 / 5 (100%)** | ≥ 4 |
| Avg. explanation score | **4.40 / 5** | ≥ 4.0 |
| Explanations scoring ≥ 4 | 14 / 15 | |

**Success criterion: MET ✅**

## 💡 What I learned

- **Write the success criterion before the prompt.** Otherwise "good enough" moves to wherever the results happen to land.
- **Edge cases are the eval.** The easy alerts pass with almost any prompt. The conflicting tags, the empty input and the garbled text are where prompt design actually matters.
- **Grade what code can grade, and use an LLM only for the rest.** Exact match is free, fast and deterministic. The LLM grader handles what has no single right answer.
- **The rubric has gaps, and the grader's reasoning shows them.** On the garbled alert (#14), the grader gave a 3: the explanation couldn't say *where* or *why it matters*, because the alert doesn't contain that information. The grader itself noted that a 4 was "defensible". The rubric never says how to treat inputs that don't contain the information. That's exactly the kind of ambiguity Step 6 is meant to catch, and the next rubric version should handle it.
- **A grader is a model, not ground truth.** It's only trusted after it agrees with a human on a sample. The classifier and grader also use the same model here, which can bias the grader in its own favor.

## ▶️ Run it

From the repo root, with `ANTHROPIC_API_KEY` set in the root `.env`:

```bash
python 01-foundations/prompt-evals/alert-severity-eval/eval.py
```

## 📁 Files

| File | Purpose |
|------|---------|
| [`eval.py`](eval.py) | Classifier prompt, code grader, LLM grader, report, grader validation |
| [`test_cases.json`](test_cases.json) | 15 alerts with expected labels and justifications |
| [`human_labels.json`](human_labels.json) | My hand scores for Step 6 |
| [`results/latest_run.json`](results/latest_run.json) | Full output of the latest run |
