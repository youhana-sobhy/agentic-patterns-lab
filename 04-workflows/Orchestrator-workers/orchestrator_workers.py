"""Orchestrator-Workers: one LLM plans the approaches, other LLM calls carry them out.

Flow:
    task -> orchestrator (plans N approaches as XML)
         -> parse every <task> block into {type, description}
         -> one worker call per approach, run in parallel
         -> print each result side by side

Run:
    python 04-workflows/Orchestrator-workers/orchestrator_workers.py
"""

import sys
from concurrent.futures import ThreadPoolExecutor

from util import extract_all_xml, extract_xml, llm_call

TASK = "Write a congratulations message to your friend"
NUM_APPROACHES = 3

# ---------------------------------------------------------------
# Prompts
# ---------------------------------------------------------------

ORCHESTRATOR_PROMPT = """\
Analyze the task below and propose {num} clearly different approaches to it.

<user_task>{task}</user_task>

Return only this block, with no extra text. Repeat <task> once per approach:

<analysis>One or two sentences on what matters most for this task.</analysis>
<tasks>
    <task>
        <type>short name of the approach</type>
        <description>what the writer should do for this approach, and when it fits best</description>
    </task>
</tasks>
"""

WORKER_PROMPT = """\
Complete the original task using the approach described below.

<original_task>{task}</original_task>
<approach>{task_type}</approach>
<guidelines>{description}</guidelines>

Return only the finished message inside <response></response> tags.
"""


# ---------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------

def plan(task: str, num: int = NUM_APPROACHES) -> tuple[str, list[dict]]:
    """Ask the orchestrator for approaches and parse them into a list of dicts."""
    raw = llm_call(ORCHESTRATOR_PROMPT.format(task=task, num=num))

    analysis = extract_xml(raw, "analysis")
    tasks_xml = extract_xml(raw, "tasks")

    # extract_xml returns ONE string. Split it into one block per <task>,
    # then pull the fields out of each block.
    approaches = [
        {
            "type": extract_xml(block, "type") or "default",
            "description": extract_xml(block, "description"),
        }
        for block in extract_all_xml(tasks_xml, "task")
    ]
    approaches = [a for a in approaches if a["description"]]

    if not approaches:
        raise ValueError(f"Orchestrator returned no usable <task> blocks:\n{raw}")

    return analysis, approaches


# ---------------------------------------------------------------
# Workers
# ---------------------------------------------------------------

def run_worker(task: str, approach: dict) -> str:
    """Carry out one approach and return the finished content."""
    raw = llm_call(
        WORKER_PROMPT.format(
            task=task,
            task_type=approach["type"],
            description=approach["description"],
        )
    )
    # Fall back to the raw reply if the model forgot the <response> tags.
    return extract_xml(raw, "response") or raw


def run(task: str) -> list[dict]:
    analysis, approaches = plan(task)

    print_header("ORCHESTRATOR ANALYSIS")
    print(analysis)

    print_header(f"{len(approaches)} APPROACHES")
    for i, approach in enumerate(approaches, 1):
        print(f"{i}. {approach['type']}\n   {approach['description']}\n")

    # Workers don't depend on each other, so they can run at the same time.
    with ThreadPoolExecutor(max_workers=len(approaches)) as pool:
        outputs = list(pool.map(lambda a: run_worker(task, a), approaches))

    results = [{**a, "result": out} for a, out in zip(approaches, outputs)]

    print_header("RESULTS")
    for i, r in enumerate(results, 1):
        print(f"--- Approach {i}: {r['type']} ---\n{r['result']}\n")

    return results


def print_header(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


if __name__ == "__main__":
    # Model replies can contain emojis, which the default Windows console encoding can't print.
    sys.stdout.reconfigure(encoding="utf-8")
    run(TASK)
