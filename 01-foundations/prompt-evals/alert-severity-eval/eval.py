"""Alert Severity Eval: an end-to-end prompt evaluation.

A classifier prompt reads a raw monitoring alert and returns a severity
(critical / warning / info) plus a one-sentence explanation. The eval grades it
two ways:

    Step 4  Code grading     the <severity> must exactly match the expected label
    Step 5  LLM grading      a second model call scores the explanation 1-5 with a rubric
    Step 6  Grader check     compare the LLM grader with my own hand labels

Run from anywhere:
    python 01-foundations/prompt-evals/alert-severity-eval/eval.py

Exit code is 0 when the Step 1 success criterion is met, 1 otherwise.
"""

import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from anthropic import Anthropic
from dotenv import load_dotenv

# ---------------------------------------------------------------
# Setup
# ---------------------------------------------------------------

LAB_DIR = Path(__file__).resolve().parent
REPO_ROOT = LAB_DIR.parents[2]  # alert-severity-eval -> prompt-evals -> 01-foundations -> repo root

# Load the ONE .env at the repo root, no matter which folder you run from.
load_dotenv(REPO_ROOT / ".env")

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError(f"ANTHROPIC_API_KEY is not set. Add it to {REPO_ROOT / '.env'}")

MODEL = "claude-sonnet-5-5"
TEST_CASES_FILE = LAB_DIR / "test_cases.json"
HUMAN_LABELS_FILE = LAB_DIR / "human_labels.json"
RESULTS_FILE = LAB_DIR / "results" / "latest_run.json"
LABELS = {"critical", "warning", "info"}

# Step 1 success criterion (see README.md)
MIN_CORRECT = 13        # out of 15
MIN_EDGE_CORRECT = 4    # out of 5
TARGET_AVG_SCORE = 4.0  # explanation quality target (reported, not part of the pass/fail)

client = Anthropic()


def llm_call(prompt: str, system: str = "", max_tokens: int = 1024) -> str:
    """Send one user prompt to Claude and return the text of the reply."""
    params = {
        "model": MODEL,
        "max_tokens": max_tokens,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        params["system"] = system

    response = client.messages.create(**params)
    return "".join(block.text for block in response.content if block.type == "text").strip()


def extract(text: str, tag: str) -> str:
    """Return the content of the first <tag>...</tag> in text, or "" if it's missing."""
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def load_test_cases() -> list[dict]:
    """Return the test cases: [{"id", "input", "expected", "edge_case", "note"}, ...]."""
    return json.loads(TEST_CASES_FILE.read_text(encoding="utf-8"))


# ---------------------------------------------------------------
# Step 3: The prompt under test
# ---------------------------------------------------------------

CLASSIFIER_SYSTEM = """You are an SRE triaging monitoring alerts for an on-call team.
Classify each alert by what it actually describes:

- critical: a production service is down or about to be, data is at risk, or users are affected now. Page someone.
- warning: something is degraded or trending toward failure, but users aren't affected yet. Act soon, not at 3 a.m.
- info: no action needed. Success messages, recoveries, no-change reports, and test alerts.

Rules:
1. Content beats the label. If the alert's own tag (INFO:, CRITICAL:) contradicts what it describes, classify by what it describes.
2. Empty or unreadable alerts are warning: a human should look, because the monitoring integration may be broken.
3. Vague but plausible problems are warning. Without evidence of impact, don't escalate to critical."""

CLASSIFIER_PROMPT = """<alert>{alert}</alert>

Respond in exactly this format and nothing else:
<severity>critical, warning, or info</severity>
<explanation>One sentence for the on-call engineer: what is wrong, where, and why it matters.</explanation>"""


def classify(alert: str) -> tuple[str, str]:
    """Run the classifier on one alert. Returns (severity, explanation)."""
    reply = llm_call(CLASSIFIER_PROMPT.format(alert=alert), system=CLASSIFIER_SYSTEM)
    return extract(reply, "severity").lower(), extract(reply, "explanation")


# ---------------------------------------------------------------
# Step 4: Code grading (exact match)
# ---------------------------------------------------------------

def code_grade(severity: str, expected: str) -> bool:
    """Pass only if the output is a valid label AND matches the expected one exactly."""
    return severity in LABELS and severity == expected.lower()


# ---------------------------------------------------------------
# Step 5: LLM grading (explanation quality, with a rubric)
# ---------------------------------------------------------------

GRADER_SYSTEM = "You are a strict reviewer of on-call alert explanations. You grade only against the rubric you are given."

GRADER_PROMPT = """Grade the explanation of this monitoring alert.

<alert>{alert}</alert>
<severity>{severity}</severity>
<explanation>{explanation}</explanation>

<rubric>
5 = one clear sentence that says what is wrong, where, and why it matters, with no unexplained jargon
4 = clear, but missing one of: what / where / why it matters
3 = understandable but vague
2 = confusing, too long, or just repeats the alert
1 = wrong, contradicts the severity, or empty
</rubric>

Judge first, then score. Respond in exactly this format:
<reasoning>Which parts of the rubric the explanation meets or misses.</reasoning>
<score>a single number from 1 to 5</score>"""


def llm_grade(alert: str, severity: str, explanation: str) -> tuple[int, str]:
    """Score one explanation with the rubric. Returns (score, reasoning); score 0 = grader broke format."""
    reply = llm_call(
        GRADER_PROMPT.format(alert=alert, severity=severity, explanation=explanation),
        system=GRADER_SYSTEM,
    )
    score_text = extract(reply, "score")
    score = int(score_text) if score_text.isdigit() and 1 <= int(score_text) <= 5 else 0
    return score, extract(reply, "reasoning")


# ---------------------------------------------------------------
# Run one case end to end
# ---------------------------------------------------------------

def run_case(case: dict) -> dict:
    severity, explanation = classify(case["input"])
    score, reasoning = llm_grade(case["input"], severity, explanation)
    return {
        "id": case["id"],
        "input": case["input"],
        "expected": case["expected"],
        "got": severity,
        "passed": code_grade(severity, case["expected"]),
        "edge_case": case["edge_case"],
        "explanation": explanation,
        "score": score,
        "grader_reasoning": reasoning,
    }


# ---------------------------------------------------------------
# Step 6: Validate the LLM grader against my hand labels
# ---------------------------------------------------------------

def validate_grader(results: list[dict]) -> None:
    """Compare grader scores with human scores in human_labels.json (if filled in)."""
    print("\nStep 6: Grader vs. human labels")
    if not HUMAN_LABELS_FILE.exists():
        print("  human_labels.json not found, skipping.")
        return

    labels = json.loads(HUMAN_LABELS_FILE.read_text(encoding="utf-8"))
    by_id = {r["id"]: r for r in results}
    pairs = [(l["id"], l["my_score"], by_id[l["id"]]["score"])
             for l in labels if l.get("my_score") is not None and l["id"] in by_id]

    if not pairs:
        print("  No hand labels yet. Score the explanations in results/latest_run.json")
        print("  with the rubric, put your scores in human_labels.json, and run again.")
        return

    print(f"  {'id':>3}  {'me':>3}  {'grader':>6}  agree (within 1)")
    for case_id, mine, grader in pairs:
        print(f"  {case_id:>3}  {mine:>3}  {grader:>6}  {'yes' if abs(mine - grader) <= 1 else 'NO'}")

    exact = sum(m == g for _, m, g in pairs)
    close = sum(abs(m - g) <= 1 for _, m, g in pairs)
    print(f"  Exact agreement: {exact}/{len(pairs)}   Within 1 point: {close}/{len(pairs)}")
    print("  Note: hand labels were scored on an earlier run's explanations; re-score if they changed.")


# ---------------------------------------------------------------
# Report
# ---------------------------------------------------------------

def report(results: list[dict]) -> bool:
    print(f"\n{'id':>3}  {'expected':<9} {'got':<9} {'pass':<5} {'edge':<5} {'score':>5}")
    print("-" * 44)
    for r in results:
        print(f"{r['id']:>3}  {r['expected']:<9} {r['got'] or '(none)':<9} "
              f"{'✅' if r['passed'] else '❌':<5} {'yes' if r['edge_case'] else '':<5} {r['score']:>5}")

    correct = sum(r["passed"] for r in results)
    edge = [r for r in results if r["edge_case"]]
    edge_correct = sum(r["passed"] for r in edge)
    scores = [r["score"] for r in results]
    avg_score = sum(scores) / len(scores)

    print("\nStep 4: Code grading (exact match)")
    print(f"  Overall accuracy:    {correct}/{len(results)} = {correct / len(results):.0%}   (target ≥ {MIN_CORRECT})")
    print(f"  Edge-case accuracy:  {edge_correct}/{len(edge)} = {edge_correct / len(edge):.0%}   (target ≥ {MIN_EDGE_CORRECT})")

    print("\nStep 5: LLM grading (explanation quality, 1-5)")
    print(f"  Average score:       {avg_score:.2f} / 5   (target ≥ {TARGET_AVG_SCORE})")
    print(f"  Scored 4 or higher:  {sum(s >= 4 for s in scores)}/{len(scores)}")
    if 0 in scores:
        print(f"  Grader format errors: {scores.count(0)}")

    met = correct >= MIN_CORRECT and edge_correct >= MIN_EDGE_CORRECT
    print(f"\nSuccess criterion: {'MET ✅' if met else 'NOT MET ❌'}")
    return met


def main() -> int:
    cases = load_test_cases()
    print(f"Running {len(cases)} test cases against {MODEL} ...")

    # Cases are independent, so run them in parallel. map() keeps the original order.
    with ThreadPoolExecutor(max_workers=5) as pool:
        results = list(pool.map(run_case, cases))

    RESULTS_FILE.parent.mkdir(exist_ok=True)
    RESULTS_FILE.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")

    met = report(results)
    validate_grader(results)
    print(f"\nFull results (explanations + grader reasoning): {RESULTS_FILE.relative_to(REPO_ROOT)}")
    return 0 if met else 1


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
