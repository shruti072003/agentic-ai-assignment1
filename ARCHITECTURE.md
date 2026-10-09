# ARCHITECTURE.md · RepoMind on the seven layers

Assignment 1, Part C item 7 (Week 1, slide 43). For each layer: what does this job,
and where is it enforced. Cite code as a file path and line number joined by a
colon, inside backticks; the checker opens every reference. A layer held only by a
sentence in a prompt (any file under `prompts/`) is **EMPTY**, and so is a layer
nothing does yet. Status is one of: present, partial (say what is missing), or
**EMPTY**. Keep this file current: later assignments fill it in.

What each layer is for (Week 1, slides 40 to 42):

- **Model**: reasoning, choosing tools, generating text.
- **Harness**: runs the loop, builds each prompt, trims old history.
- **Tools**: where the system acts on the world.
- **Memory & State**: what survives a step, a session, a restart.
- **Control & Policy**: what the system may do, and when it must ask.
- **Observability**: a step-by-step record of what it did.
- **Evaluation**: measuring quality, before and after release.

| Layer | What does this job | Where it is enforced | Status |
|---|---|---|---|
| Model | gpt-4.1-mini. It's named in one place in settings and stays the same across all four ways, and every call goes through the metered client | `settings.yaml:24`, `harness/client.py:116` | present |
| Harness | My own loop. Each request is built from the message list, every assistant turn and tool result gets appended, and the model is told how many calls it has left. The agent way uses this loop; the direct call and the workflow each have their own fixed harness | `agent/loop.py:75`, `agent/loop.py:99`, `ways/agent.py:14`, `ways/workflow.py:66` | partial: nothing trims old history, so the prompt gets longer every step (this is the A in the worst case) |
| Tools | read_issue, search_repo and post_comment, all behind one registry. Search returns at most 20 results and skips config/ | `tools/__init__.py:52`, `tools/search_repo.py:23`, `tools/post_comment.py:18` | present |
| Memory & State | Just the message list inside a run, which is gone when the run ends. The tracker keeps the comments, but no run ever reads them back | `agent/loop.py:57` | partial: state lasts across steps, but nothing lasts across sessions or restarts |
| Control & Policy | Three bounds checked in code before every model call, plus the harness's per-run ceiling in the client, the lab ceiling in the runner, and the workflow's fixed cap on searches | `agent/loop.py:63`, `agent/loop.py:66`, `agent/loop.py:70`, `harness/client.py:118`, `harness/runner.py:148`, `ways/workflow.py:18` | partial: these limit how much it spends, not what it does. Nothing prevents a second comment, a comment on the wrong issue, or private code quoted in a public comment, and nobody approves a post. "Post exactly one comment" only lives in a prompt |
| Observability | A trace line for every model call and every tool call, with tokens, cost and latency, plus the reason the run ended and its metered totals | `harness/trace.py:38`, `harness/trace.py:52`, `agent/loop.py:76`, `agent/loop.py:95`, `harness/runner.py:119` | present |
| Evaluation | A grounded check that reads only the tracker, and a script that rebuilds every table from the traces | `eval/check_triage.py:25`, `eval/summarize.py:182` | partial: offline only, on eight fixed issues with known answers; nothing measures quality after release |

**Empty layers:** 0 of 7, with four partial. Slide 46 says a first build is usually
missing four layers: memory and state, control and policy, observability, and
evaluation. Mine looks covered on paper, but mostly because the course harness
already gave me the trace writer, the ceilings and the grounded check. What I added
myself was mainly the bounds. Where it counts, memory and control are still close to
empty. Nothing carries over from one run to the next, and every rule about *what* the
system may post (one comment, on the right issue, nothing private in it) is a
sentence in a prompt, which by this file's own rule doesn't count.
