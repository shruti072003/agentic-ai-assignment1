# CHANGES.md

Three lines per assignment: what it added, what it removed, what it constrained.
Removals are logged like additions.

## Assignment 1
- **Added:** a loop (`agent/loop.py`), a model (gpt-4.1-mini) and three tools (read_issue, search_repo, post_comment), used four ways: direct call, workflow, agent and a hybrid that hands off to the agent.
- **Removed:** nothing.
- **Constrained:** the loop by three bounds checked in code before every call: 12 steps, 60,000 tokens and 180 seconds (`agent/bounds.yaml`).
