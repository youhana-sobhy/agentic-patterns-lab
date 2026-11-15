"""Shared helpers for the orchestrator-workers lab: one LLM call and XML parsing."""

import os
import re

from anthropic import Anthropic
from dotenv import load_dotenv

load_dotenv()  # reads ANTHROPIC_API_KEY from the nearest .env file

if not os.getenv("ANTHROPIC_API_KEY"):
    raise RuntimeError("ANTHROPIC_API_KEY is not set. Copy .env.example to .env and add your key.")

DEFAULT_MODEL = "claude-sonnet-5-5"

client = Anthropic()  # created once and reused by every call


def llm_call(prompt: str, system_prompt: str = "", model: str = DEFAULT_MODEL) -> str:
    """Send one user prompt to Claude and return the text of the reply."""
    params = {
        "model": model,
        "max_tokens": 4096,
        "messages": [{"role": "user", "content": prompt}],
    }
    if system_prompt:
        params["system"] = system_prompt

    response = client.messages.create(**params)
    return "".join(block.text for block in response.content if block.type == "text").strip()


def extract_xml(text: str, tag: str) -> str:
    """Return the content of the FIRST <tag>...</tag> in text, or "" if it is missing."""
    match = re.search(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)
    return match.group(1).strip() if match else ""


def extract_all_xml(text: str, tag: str) -> list[str]:
    """Return the content of EVERY <tag>...</tag> in text, in order.

    extract_xml() stops at the first match, so use this one to loop over
    repeated blocks such as several <task> entries.
    """
    return [m.strip() for m in re.findall(f"<{tag}>(.*?)</{tag}>", text, re.DOTALL)]
