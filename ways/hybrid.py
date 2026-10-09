"""Way 4, the hybrid (Part D). The workflow runs first; the agent takes the issue
only when a rule, computed from what the workflow saw, says the workflow is likely
wrong. Exactly one comment either way: the workflow posts, or the agent does.

The rule: the workflow chose a label other than question, and the file it chose
appears in none of its search results. Then the choice was a guess from the issue
text, not something the search found (or it named a file that does not exist).
"""

from __future__ import annotations

from harness.formats import normalize_path
from ways import agent, workflow


def searched_paths(found: workflow.Gathered) -> set[str]:
    """Every file that appeared in a search result line (path:line: excerpt)."""
    paths = set()
    for _, text in found.searches:
        for line in text.splitlines():
            path, sep, _ = line.partition(":")
            if sep:
                paths.add(normalize_path(path))
    return paths


def should_hand_off(found: workflow.Gathered, choice: workflow.Choice) -> bool:
    return choice.label != "question" and normalize_path(choice.file) not in searched_paths(found)


def run(ctx) -> None:
    found = workflow.gather(ctx)
    choice = workflow.choose(ctx, found)
    if should_hand_off(found, choice):
        agent.run(ctx)
    else:
        workflow.post(ctx, choice)
