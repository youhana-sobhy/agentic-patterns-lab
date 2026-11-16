"""Evaluator-Optimizer: beginner-friendly explainer generator.

Flow:
    generate -> code checks + LLM checks -> problems?
        no  -> done
        yes -> send problems + previous attempt back to the generator, repeat
    (stop after MAX_ROUNDS and report that it did not pass)
"""

import json
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads ANTHROPIC_API_KEY from .env

client = Anthropic()
model = "claude-sonnet-5-5"

MAX_ROUNDS = 3
MAX_WORDS = 100

# Each criterion is defined ONCE and reused by the generator and the checkers.
# Checked by code: LENGTH_RULE, QUESTION_RULE
# Checked by Claude: ANALOGY_RULE, TERMS_RULE
LENGTH_RULE = f"Under {MAX_WORDS} words."
ANALOGY_RULE = "Contains exactly one everyday analogy."
TERMS_RULE = "No technical terms without an explanation."
QUESTION_RULE = "Ends with a single question that tests the reader's understanding."

REQUIREMENTS = [LENGTH_RULE, ANALOGY_RULE, TERMS_RULE, QUESTION_RULE]

SYSTEM_GENERATOR = (
    "You are a patient teacher who explains technical topics to complete beginners. "
    "Reply with the explanation only, with no preface."
)

SYSTEM_EVALUATOR = (
    "You are a strict evaluator. Judge only the criteria you are given. "
    "If a criterion is only partly met, it fails."
)


# ---------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------

def ask(prompt, system=None):
    params = {
        "model": model,
        "max_tokens": 600,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system:
        params["system"] = system
    response = client.messages.create(**params)
    return "".join(b.text for b in response.content if b.type == "text").strip()


def parse_json(raw):
    # Models sometimes wrap JSON in ```json fences. Strip them, then parse.
    cleaned = re.sub(r"^```(?:json)?|```$", "", raw.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
        return {"pass": False, "issues": [f"Evaluator returned non-object JSON: {raw[:100]}"]}
    except json.JSONDecodeError:
        # A broken evaluator reply counts as a FAILURE, never as a pass.
        return {"pass": False, "issues": [f"Evaluator returned invalid JSON: {raw[:100]}"]}


# ---------------------------------------------------------------
# Generator
# ---------------------------------------------------------------

def generate(question, feedback=None, previous=None):
    requirements = "\n".join(f"- {r}" for r in REQUIREMENTS)
    prompt = (
        f"Write a short explanation for this question:\n"
        f"<user_question>{question}</user_question>\n\n"
        f"Requirements:\n{requirements}"
    )

    if feedback and previous:
        # The optimizer part: show the old attempt AND what was wrong with it.
        prompt += (
            f"\n\nYour previous attempt:\n<previous>\n{previous}\n</previous>\n\n"
            f"Problems found with it:\n<problems>\n{feedback}\n</problems>\n\n"
            f"Rewrite the explanation and fix all the problems."
        )

    return ask(prompt, system=SYSTEM_GENERATOR)


# ---------------------------------------------------------------
# Evaluators
# ---------------------------------------------------------------

def code_checks(text):
    """Things code can measure exactly."""
    problems = []

    words = len(text.split())
    if words >= MAX_WORDS:
        problems.append(f"Too long: {words} words, must be under {MAX_WORDS}.")

    # Covers both "ends with a question" and "only one question".
    # (Checks both the Latin "?" and the Arabic "؟".)
    question_marks = text.count("?") + text.count("؟")
    if question_marks != 1 or not text.rstrip().endswith(("?", "؟")):
        problems.append(
            f"Must end with exactly one question; found {question_marks} question mark(s) "
            f"and the text {'does' if text.rstrip().endswith(('?', '؟')) else 'does not'} end with one."
        )

    return problems


def llm_evaluate(text):
    """Things only a model can judge."""
    prompt = (
        "Review this message against exactly two criteria:\n\n"
        f"1. {ANALOGY_RULE}\n"
        f"2. {TERMS_RULE}\n\n"
        f"<message>\n{text}\n</message>\n\n"
        "Reply with JSON only, in this shape:\n"
        '{"pass": true or false, "issues": ["short description of each failed criterion"]}\n'
        "Use an empty list for issues when pass is true."
    )
    raw = ask(prompt, system=SYSTEM_EVALUATOR)
    return parse_json(raw)


# ---------------------------------------------------------------
# The loop
# ---------------------------------------------------------------

def run(question):
    answer, feedback = None, None

    for round_no in range(1, MAX_ROUNDS + 1):
        answer = generate(question, feedback=feedback, previous=answer)

        problems = code_checks(answer)
        verdict = llm_evaluate(answer)
        if not verdict.get("pass", False):
            # A failing verdict with no listed issues must still count as a failure.
            problems += verdict.get("issues") or ["Evaluator failed the text without listing issues."]

        print(f"\n--- Round {round_no} ---")
        print(answer)
        print("Problems:", problems if problems else "none")

        if not problems:
            return {"text": answer, "rounds": round_no, "passed": True}

        feedback = "\n".join(f"- {p}" for p in problems)

    # Out of rounds: return the last attempt, but say it did NOT pass.
    return {"text": answer, "rounds": MAX_ROUNDS, "passed": False}


if __name__ == "__main__":
    result = run("What is NAT in networks?")
    print("\n=== Final ===")
    print(result["text"])
    print(f"passed={result['passed']} after {result['rounds']} round(s)")