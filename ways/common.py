"""Helpers the ways share: loading prompts with the shared label definitions, and
reading the JSON answer a model gives when your code, not the model, posts."""

from __future__ import annotations

import json
import re

from harness.formats import LABELS

_JSON = re.compile(r"\{.*\}", re.DOTALL)


def system_prompt(ctx, name: str) -> str:
    """prompts/<name>, with {labels} replaced by prompts/labels.md, so every way
    sends the same label definitions."""
    return ctx.prompt(name).replace("{labels}", ctx.prompt("labels.md").strip())


def parse_json(text: str) -> dict:
    """The first {...} in a model's answer, or {} if there is none or it does not parse."""
    match = _JSON.search(text or "")
    if not match:
        return {}
    try:
        value = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def label_and_file(answer: dict) -> tuple[str, str]:
    """A label from the closed set and a file, from a parsed answer. An answer
    outside the set still gets posted, so that the run leaves one comment and fails
    on the tracker rather than leaving nothing."""
    label = str(answer.get("label") or "").strip().lower()
    if label not in LABELS:
        label = label or "unknown"
    file = str(answer.get("file") or "none").strip()
    if label == "question":
        file = "none"
    return label, file
