"""Way 2, the workflow. Your code decides every step, in advance, in this order:

    read_issue  ->  one call to extract search terms  ->  search_repo
                ->  one call to choose the label and the file  ->  post_comment

A fixed sequence, no loop: the model never chooses a tool. Part D reuses the two
halves: gather() (read, extract, search) and choose() (pick label and file);
post() is the last step.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from harness.formats import format_triage_comment
from ways.common import label_and_file, parse_json, system_prompt

MAX_TERMS = 5          # searches per run
RESULTS_PER_TERM = 10


@dataclass
class Gathered:
    issue: str
    terms: list[str]
    searches: list[tuple[str, str]] = field(default_factory=list)   # (term, result text)


@dataclass
class Choice:
    label: str
    file: str
    reason: str


def gather(ctx) -> Gathered:
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number}).content
    response = ctx.client.create(system=system_prompt(ctx, "workflow_terms.md"),
                                 messages=[{"role": "user", "content": f"Issue:\n\n{issue}"}])
    ctx.trace.model_call(1, response)
    raw = parse_json(response.text).get("terms") or []
    terms = [str(t).strip() for t in raw if str(t).strip()][:MAX_TERMS]
    found = Gathered(issue, terms)
    for term in terms:
        result = ctx.call_tool(1, "search_repo", {"query": term, "max_results": RESULTS_PER_TERM})
        found.searches.append((term, result.content))
    return found


def choose(ctx, found: Gathered) -> Choice:
    results = "\n\n".join(f'Search "{term}":\n{text}' for term, text in found.searches) or "(no searches)"
    message = f"Issue:\n\n{found.issue}\n\nSearch results:\n\n{results}"
    response = ctx.client.create(system=system_prompt(ctx, "workflow_choose.md"),
                                 messages=[{"role": "user", "content": message}])
    ctx.trace.model_call(2, response)
    answer = parse_json(response.text)
    label, file = label_and_file(answer)
    return Choice(label, file, str(answer.get("reason") or ""))


def post(ctx, choice: Choice) -> None:
    body = format_triage_comment(choice.label, choice.file, choice.reason)
    ctx.call_tool(2, "post_comment", {"number": ctx.issue_number, "body": body})


def run(ctx) -> None:
    post(ctx, choose(ctx, gather(ctx)))
