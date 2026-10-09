"""Way 3, the agent. The model decides, at runtime, what to call and when to stop.

Load your bounds (agent.loop.load_bounds()), then call agent.loop.run_loop with
ctx.client, ctx.tools (all three tools), a system prompt from prompts/, and a
first user message naming the issue. The agent posts its own comment through
post_comment. Your loop writes the trace, including trace.end.
"""

from agent.loop import load_bounds, run_loop
from ways.common import system_prompt


def run(ctx) -> None:
    run_loop(ctx.client, ctx.tools, system_prompt(ctx, "agent.md"),
             f"Triage issue #{ctx.issue_number}.", load_bounds(), ctx.trace)
