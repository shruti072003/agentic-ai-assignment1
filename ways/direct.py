"""Way 1, the direct call. Nobody decides the next step: there is one step.

Read the issue, make ONE model call that gets the issue plus ctx.repo_summary and
no tools, turn its answer into a comment with harness.formats.format_triage_comment,
and post it. Your code posts the comment, not the model.
"""

from harness.formats import format_triage_comment
from ways.common import label_and_file, parse_json, system_prompt


def run(ctx) -> None:
    issue = ctx.call_tool(0, "read_issue", {"number": ctx.issue_number}).content
    message = f"Repository summary:\n\n{ctx.repo_summary}\n\nIssue:\n\n{issue}"
    response = ctx.client.create(system=system_prompt(ctx, "direct.md"),
                                 messages=[{"role": "user", "content": message}])
    ctx.trace.model_call(1, response)
    answer = parse_json(response.text)
    label, file = label_and_file(answer)
    body = format_triage_comment(label, file, str(answer.get("reason") or ""))
    ctx.call_tool(1, "post_comment", {"number": ctx.issue_number, "body": body})
