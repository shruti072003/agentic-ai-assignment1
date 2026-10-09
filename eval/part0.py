"""Part 0: read the recorded run and measure how its prompt grew.

    python -m eval.part0              # print the numbers
    python -m eval.part0 --write      # also put them in reports/LAB_01.json
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RECORDING = ROOT / "fixtures" / "week01_recorded_run.jsonl"
REPORT = ROOT / "reports" / "LAB_01.json"


def prompt_tokens(usage: dict) -> int:
    return (usage.get("input_tokens", 0)
            + usage.get("cache_read_input_tokens", 0)
            + usage.get("cache_creation_input_tokens", 0))


def measure(path: Path = RECORDING) -> dict:
    calls: dict[str, dict] = {}   # message.id -> usage, in first-seen order
    tool_calls = 0
    for line in path.read_text().splitlines():
        if not line.strip():
            continue
        event = json.loads(line)
        if event.get("type") != "assistant":
            continue
        message = event["message"]
        calls[message["id"]] = message.get("usage", {})
        tool_calls += sum(1 for b in message.get("content", []) if b.get("type") == "tool_use")

    usages = list(calls.values())
    prompts = [prompt_tokens(u) for u in usages]
    total = sum(prompts)
    cached = sum(u.get("cache_read_input_tokens", 0) for u in usages)
    return {
        "model_calls": len(usages),
        "tool_calls": tool_calls,
        "prompt_tokens": total,
        "cache_read_tokens": cached,
        "cache_read_share": round(cached / total, 4) if total else None,
        "first_prompt": prompts[0],
        "last_prompt": prompts[-1],
        "cumulative_over_first": round(total / prompts[0], 2) if prompts[0] else None,
    }


def main(argv: list[str]) -> None:
    numbers = measure()
    for key, value in numbers.items():
        print(f"{key:<24} {value:,}" if isinstance(value, int) else f"{key:<24} {value}")
    if "--write" in argv:
        report = json.loads(REPORT.read_text())
        report["part0"] = numbers
        REPORT.write_text(json.dumps(report, indent=2) + "\n")
        print(f"\nwrote part0 to {REPORT.relative_to(ROOT)}")


if __name__ == "__main__":
    main(sys.argv[1:])
