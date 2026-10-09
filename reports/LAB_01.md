# Assignment 1 report · Four ways to triage an issue

Every number here is also in `reports/LAB_01.json`, which is what the checker reads
(format: `checks/FORMATS.md`, section 7). I used one model for every run,
gpt-4.1-mini through the OpenAI API. Prices come from `pricing.yaml`, which I
copied from https://developers.openai.com/api/docs/pricing on 2026-10-07 (vendor
price page): $0.40 per million input tokens, $0.10 per million cached input
tokens and $1.60 per million output tokens.

## Part 0 · The recorded trace

Numbers from `fixtures/week01_recorded_run.jsonl`, computed by `eval/part0.py` (a single recording, so n = 1):

| Measure | Value |
|---|---|
| Model calls (distinct `message.id`) | 21 |
| Tool calls | 23 |
| Prompt tokens, all calls | 399,123 |
| Cache reads | 388,338 (0.973 of the prompt) |
| First call's prompt | 13,445 |
| Last call's prompt | 24,188 |
| Cumulative over first | 29.7 |

From the first call to the last, the prompt grew only 1.8×, yet the whole run read 29.7× the first prompt, because every call re-sends everything that came before it.

## Part A · Your loop's bounds

The bounds live in `agent/bounds.yaml`, and `agent/loop.py` checks all three before every model call:

- **max_steps: 12.** A good run reads the issue, does a few searches and posts, which is about 6 calls. Twelve allows a second round of searching. An agent that needs more than that is going in circles.
- **max_tokens: 60,000.** About three times my estimated worst case at 12 steps, so it only kicks in if search results are much bigger than I expect. It also sits well under the harness ceiling of 400,000.
- **wall_clock_s: 180.** A normal run takes under 30 seconds. Three minutes leaves time for rate-limit waits and still stops a stuck run.

**Worst case,** N·F + A·N(N−1)/2 with N = 12:

| | F | A | N | Cumulative prompt tokens |
|---|---|---|---|---|
| Estimated before any run (characters / 4 of my system prompt, the three tool schemas and a few sample search results) | 658 | 188 | 12 | 20,304 |
| Measured on the 60 evaluation agent runs (in `LAB_01.json`) | 725.0 | 146.2 | 12 | 18,349 |

I guessed F too low, because counting characters misses the tokens OpenAI adds to format tools. I guessed A too high, because most searches return one line or "No matches.". The two errors roughly cancelled out. The 60,000 budget ended up about 3× above the measured worst case. In the real runs the token budget never fired, and every run that a bound stopped (24 of 60) was stopped by the turn limit.

**`make bounds-smoke`:** both dev runs against NeverStops end on `turn_limit` after exactly 12 model calls, having used 20,204 estimated prompt tokens. That is far below 60,000, so the step limit binds before the token budget. The checker's own run came to 32,531 cumulative prompt tokens, under its limit of 31,398 × 1.15. The extra tokens come from a one-line "[harness] N model calls left" note that my loop adds after each tool result.

That note is the only change I made to the loop during dev tuning. Before it, the agent on 4191 found `README.md:52: npm run serve` on its second call and then kept searching until the turn limit, without ever posting. Prompt changes alone got 2 of 6 dev runs to post. With the counter added, 5 of 6 posted, and every dev run that posted got the right answer.

## Part B · Results

Each way ran 60 times (6 evaluation issues × 10 sweeps), all after `make reset`, with `--jobs 4` on gpt-4.1-mini. `eval/check_triage.py` reads success from `tracker/comments.jsonl`, and `eval/summarize.py` builds the table.

| Measure | Direct | Workflow | Agent |
|---|---|---|---|
| Passes / 60 | **40** | 29 | 28 |
| 4201 (reset link points to localhost) / 10 | 10 | 9 | 10 |
| 4202 (TSV export) / 10 | 10 | 10 | 2 |
| 4203 (Malformed row on row 1) / 10 | 10 | 0 | 8 |
| 4204 (Monday email on Tuesday) / 10 | 0 | 0 | 0 |
| 4205 (do you keep uploads?) / 10 | 10 | 10 | 8 |
| 4206 (currencies merged in CSV) / 10 | 0 | 0 | 0 |
| Spread: lowest–highest sweep (of 6) | 4–4 | 2–3 | 1–4 |
| Issues solved in all 10 runs | 4 | 2 | 1 |
| Mean prompt tokens / run | 1,070 | 875 | 13,049 |
| of which cached | 0 | 0 | 3,403 |
| uncached | 1,070 | 875 | 9,646 |
| Mean output tokens / run | 47 | 78 | 251 |
| Latency p50 / p95 (s) | 0.84 / 1.23 | 1.62 / 1.95 | 7.24 / 8.57 |
| Mean cost / run (USD, prices read 2026-10-07) | 0.000504 | 0.000474 | 0.004601 |
| Tool calls mean / max | 2.00 / 2 | 6.87 / 7 | 8.77 / 12 |

OpenAI caches long, repeated prompts automatically. Only the agent's prompts are long enough to qualify, which is why it is the only way with cached tokens. Each call's `cost_usd` already prices those tokens at the cache rate.

Of the agent's 60 runs, 36 ended `model_stopped` and 24 ended `turn_limit`. Eight of the turn-limit runs never posted a comment: 3 on 4202, 2 on 4203, 2 on 4205 and 1 on 4206. The other 16 posted in their last few steps.

## Part C · The decision

### 1. Find the diamond

In none of the four ways does a person approve a step: the comment goes straight onto a public issue. So none of them is a chatbot or a copilot. What separates them is who picks the next step and who ends the run.

| Way | Who picks the next step | Who ends the run | What it is |
|---|---|---|---|
| Direct | My code (`ways/direct.py`): read, one call, post. There is only one path | My code, after the post | A script. The model fills in the label and file, but doesn't decide what happens next |
| Workflow | My code (`ways/workflow.py`), always read → terms → up to 5 searches → choose → post | My code | A workflow. The model chooses the search terms and the final answer, never which tool runs or when the run stops |
| Agent | The model, every step (`agent/loop.py` hands it all three tools) | The model in 36 of 60 runs (`model_stopped`), my code's turn limit in the other 24 | An agent inside a fence that my code controls. The diamond is in the model, and the model also chooses to publish |
| Hybrid (Part D) | My code first, then the model if the rule fires | My code if the workflow keeps the issue, otherwise the model or the bounds | A workflow with one diamond in code (`ways/hybrid.py`) that decides whether an agent takes over |

Looked at part by part, even the agent is mostly code: the bounds, the trace and the success check are all fixed there. The only things the model took over are which tool comes next and when to stop.

### 2. Your multipliers

- **Agent tokens / direct tokens:** (13,049 + 251) / (1,070 + 47) = **11.9×**. The lecture's figure is ≈4× (slide 30; Anthropic-reported, one team, its own workload, 2025). That is a vendor's number that I'm quoting; I didn't measure it.
- Two ways their measurement differs from mine:
  1. **The baseline.** Theirs is a chat interaction, a person in a conversation that already carries context. Mine is one call with no tools and a fixed ~800-token repo summary, about as cheap as this task can be done. With that small a denominator, the ratio comes out big.
  2. **The workload and the cap.** Theirs is a team's real, mixed work on a frontier model, where long agent sessions get cached heavily. Mine is one narrow task, six synthetic issues, gpt-4.1-mini and a hard limit of 12 steps. The limit cuts off the long tail that would push the ratio up, and only 26% of my agent's prompt tokens were cached.
- **m, agent cost / workflow cost:** 0.004601 / 0.000474 = **9.70**.

### 3. Where the agent earns it

f counts the issues where the workflow passes fewer than 5 of 10 and the agent passes 5 or more. Only **4203** qualifies (workflow 0, agent 8), so **f = 1/6 = 0.167**. With c = $0.000474, the workflow's cost per run:

| Design | Cost per run |
|---|---|
| Workflow alone, c | $0.000474 |
| Blended, c × [(1 − f) + f × m] = c × (0.833 + 0.167 × 9.70) | **$0.001162** (2.45 × c) |
| Everything through the agent, c × m | $0.004601 |

**The slide's version, against the direct call:** c = $0.000504, m = 9.13 and f = 0, so the blended cost is just c = $0.000504.

f comes out 0 because the direct call already gets 4203 right 10 times out of 10, and the only issues it fails, 4204 and 4206, the agent fails as well. With f at 0, the handout asks for the cost of each extra correct triage. The agent costs $0.004097 more per run and passes fewer runs (0.467 per run against 0.667), so there's nothing extra to pay for. Against the workflow, too, the agent passes one run fewer in 60 (28 against 29).

**Which baseline gate 4 should use: the direct call.** The handout picks the workflow because it is "the design you would ship if the agent lost". On my data, though, the design I'd ship in that case is the direct call. It has the most passes (40), the steadiest sweeps (4 every time) and the best p95 latency, at about the workflow's cost. Measured against it, f is 0. The workflow version, f = 1/6, makes the agent look useful on 4203 only because my workflow is bad at 4203, not because 4203 needs an agent.

### 4. Path entropy

Across the agent's 60 runs I count **27 distinct tool-call sequences, and the three most common cover 40%** (24 runs):

- read, ten searches, post (11 runs);
- read and post, with no search at all (7);
- read, two searches, read again, post (6).

Most of that variety is wasted motion, not exploration that pays off. 33 of the 60 runs repeat a query they had already run, and 38 re-read an issue they had already read. The agent averages 6.15 searches per run, and most return "No matches." or the same CHANGELOG lines.

So the part not earning its cost is the model choosing the next step. Every run uses the same three moves, read, search and post. All the model varies is how many searches it does before giving up, and as 4202 and 4204 show, searches after the third rarely changed the answer.

### 5. The four gates

1. **Does the task vary case to case?** Hardly: every issue goes read, search, decide, post, and the agent's 27 paths are mostly repeats of that.
2. **Can you limit the damage of a mistake?** Partly: a bad comment is one deletable post, but no code limits what the agent writes into it or how many it posts.
3. **Will you catch it in time?** No: nobody checks before posting, and the 8 agent runs that never posted were found only by the tracker check afterwards.
4. **Is it worth the multiplier?** No: 9.70× the workflow's cost (9.13× the direct call's) for 28 passes against 29 and 40, and 7× slower at p95.

**Verdict (before Part D): workflow.** Control flow should stay in my code, and the design to ship is the simplest workflow, the direct call, which beat my searching workflow on these six issues.

Nothing solves 4204 or 4206. Both need the code to be read, and `search_repo` returns single lines in path order, so CHANGELOG and docs lines crowd out the source. With these tools an agent can't fix that. Part D tests whether a hybrid changes the picture.

### 6. Your predictions

These are from `reports/PREDICTIONS_01.md`, which I pushed before the evaluation runs.

- **Direct: predicted 32, got 40.**
  - *What I believed:* without access to the code it would have to guess from filenames, and would miss 4201 and 4203.
  - *What happened:* the repo summary as good as names both files ("Email bodies" for the templates, "Parses an uploaded CSV statement into rows" for the parser). Every `direct-4201-*` and `direct-4203-*` trace picks the right file in all 10 runs.
  - *Hardest issue:* I picked 4206, which was right but only a tie; 4204 also scored 0.

- **Workflow: predicted 36, got 29.**
  - *What I believed:* searching would correct the direct call's guesses.
  - *What happened:* searching made 4203 worse, from 10/10 to 0/10. In `runs/workflow-4203-s01-2e8bc8.jsonl` the term step picks the quoted error text and two function names it invented. The only hit is that error string in `src/i18n/en.json`. The choose step, told to "choose the most likely path anyway", then makes up `src/import/csv.ts`, a file that doesn't exist. Over ten runs it gave seven different wrong paths. Unlike the direct call, the workflow never sees the repo summary, and the summary is what gave the direct call its right answers.
  - *Hardest issue:* 4206 did score 0/10, but tied with 4203 and 4204.

- **Agent: predicted 38, got 28; I said 4204 would be hardest.**
  - *4204:* it was 0/10, but not for the reason I gave. I expected answers spread across several files. Instead the agent said `src/notifications/rollup.ts` all 10 times. In `runs/agent-4204-s01-3246c9.jsonl` its searches only reach CHANGELOG and docs lines about the rollup, and it never sees the date helper.
  - *4206:* just as consistently wrong (`runs/agent-4206-s01-a0bfad.jsonl`). It searched `writeCsv`, landed on the file the reporter had named and posted that. I'd expected this to be the one way that looked past the title.
  - *4202:* 2/10, which I didn't see coming at all. In `runs/agent-4202-s02-1f39b7.jsonl` it searches "export format" twice (one i18n string) and "export" twice (CHANGELOG lines). It only reaches `src/exportUtils.ts` through "delimiter", on its 11th call, and hits the turn limit before posting.
  - *What I got about right:* how often it never posts. I guessed one run in six, and it was 8 of 60.

### 7. The seven-layer audit

According to `ARCHITECTURE.md`, **0 of 7 layers are empty, and four are partial**: harness, memory & state, control & policy, and evaluation. Slide 46 expects a first build to be missing four layers: memory and state, control and policy, observability and evaluation.

Of those four, observability and evaluation are present here only because the course harness provided the trace writer and the grounded check. Memory and control are partial in a way that's close to empty. Nothing carries over from one run to the next, and the bounds limit how much the system spends but not what it does. The rule that matters most for a public comment, post exactly one and only about this issue, exists only as a sentence in `prompts/agent.md`.

## Part D · The hybrid

### The hand-off rule, written before measuring

**Rule:** after the workflow's choose step, hand the issue to the agent instead of posting when the chosen label isn't `question` **and** the chosen file shows up in none of the workflow's own search results (`ways/hybrid.py`). If the search found the file, the choice rests on something the workflow actually saw. If it didn't, the choice is a guess from the issue's wording, or a file that doesn't exist.

**The traces behind it.** The trace keeps only 300 characters of each result, so I re-ran every search from the workflow's 60 Part B runs to get the full results; the tool is deterministic. Here is how often each of the three suggested starting points would have fired:

| Rule | 4201 | 4202 | 4203 | 4204 | 4205 | 4206 |
|---|---|---|---|---|---|---|
| Every search returned "No matches." | 1 | 0 | 0 | 0 | 9 | 0 |
| Chosen file is in no search result (not a question) | 1 | 0 | **7** | 0 | 0 | 7 |
| No file chosen for something other than a question | 0 | 0 | 0 | 0 | 0 | 0 |

- **The first rule** mostly fires on 4205, the question, which the workflow already gets right.
- **The third rule** never fires.
- **The second rule** fires on 7 of the 10 failing 4203 runs, the ones with invented paths like `runs/workflow-4203-s01-2e8bc8.jsonl`. In the other 3 the workflow named `src/i18n/en.json`, which was in its results. On the issues the workflow passes, the rule fires once in 30 runs.
- **The second rule's cost:** it also fires on 7 runs of 4206, where the agent passed 0 of 10, so I expect those hand-offs to cost money and recover nothing. It never fires on 4204, where the workflow picks `src/api/users.ts`, a file its search did find.

**What I expect:** about 15 hand-offs, and about 5–6 extra passes on 4203 (7 hand-offs × the agent's 0.8), for roughly 34–35 of 60. Cost should be about c + 0.25 × the agent's cost ≈ $0.0016 per run. That is a little above the $0.00116 blended cost, since a quarter of runs go to the agent rather than f = 1/6.

**This result is optimistic.** I chose the rule by looking at the same six issues I'm about to measure it on, and on new issues it might fire in the wrong places.

### Results, measured after the rule was written

60 runs with `python run.py --way hybrid --set eval --runs 10`, without a reset beforehand.

| Measure | Direct | Workflow | Agent | Hybrid |
|---|---|---|---|---|
| Passes / 60 | **40** | 29 | 28 | 38 |
| 4201 / 10 | 10 | 9 | 10 | 10 |
| 4202 / 10 | 10 | 10 | 2 | 10 |
| 4203 / 10 | 10 | 0 | 8 | 8 |
| 4204 / 10 | 0 | 0 | 0 | 0 |
| 4205 / 10 | 10 | 10 | 8 | 10 |
| 4206 / 10 | 0 | 0 | 0 | 0 |
| Spread: lowest–highest sweep | 4–4 | 2–3 | 1–4 | 3–4 |
| Issues solved in all 10 runs | 4 | 2 | 1 | 3 |
| Mean prompt tokens (cached) | 1,070 (0) | 875 (0) | 13,049 (3,403) | 7,318 (3,136) |
| Mean output tokens | 47 | 78 | 251 | 181 |
| Latency p50 / p95 (s) | 0.84 / 1.23 | 1.62 / 1.95 | 7.24 / 8.57 | 1.76 / 10.17 |
| Mean cost / run (USD) | 0.000504 | 0.000474 | 0.004601 | **0.002276** |
| Tool calls mean / max | 2.00 / 2 | 6.87 / 7 | 8.77 / 12 | 10.58 / 18 |

**Hand-offs: 22 of 60.** This is `hybrid_handoffs`, counted from end records that aren't `completed`; 11 of them ended `model_stopped` and 11 `turn_limit`. By issue: 8 on 4203, 10 on 4206, 3 on 4204, 1 on 4202, and none on 4201 or 4205.

**Where they landed.**

- **Useful: 9.** Part C found exactly one issue where the agent earns its cost, 4203, and that is where the rule did its job. It handed off 8 of the 10 runs on 4203, and all 8 passed. The 2 runs it kept in the workflow named `src/i18n/en.json`, which the search had found, and both failed. The single hand-off on 4202 also passed.
- **Wasted: 13.** All 10 runs of 4206 went to the agent: 7 posted the reporter's `src/export/csv.ts` again and 3 posted nothing. 3 runs of 4204 went to the agent too, and 2 of those posted nothing.
- **Why it fired more than predicted.** It fired more often than it would have on the Part B workflow traces (10 against 7 on 4206, 3 against 0 on 4204). The workflow picks different search terms from run to run, and the rule depends on what those searches return.
- **No comment.** 5 of the 22 hand-offs ended without a comment, so the hybrid also inherits the agent's habit of never posting.

**Measured cost against the blended cost.** The hybrid cost $0.002276 per run, against the $0.001162 blended cost from Part C, item 3: **1.96×** the prediction. Two things explain the gap.

1. **The rule fired much more often than f.** The blended cost assumes that only the issues where the agent earns its cost get handed off, f = 1/6 of runs. My rule handed off 22/60 = 0.37 of runs, more than double, and 13 of those 22 went to issues the agent can't win.
2. **A hand-off pays for both the workflow and the agent.** The formula charges m × c for a handed-off run. My hybrid runs the whole workflow first, then starts the agent from scratch, and the agent re-reads the issue and repeats searches the workflow had already done. The agent part of each hand-off cost about $0.0049, on top of the workflow's $0.00047.

As a check, c + (22/60) × $0.0049 = $0.00227, which matches what I measured.

**Does it change the Part C verdict? No.** The hybrid did what Part D asked. It got 38 passes against the workflow's 29, at about half the agent's cost, and it gave the agent only the cases where the workflow's search came back empty. My Part C baseline, though, is the direct call, not the workflow. Against the direct call:

- **Accuracy:** the hybrid is 2 passes worse, 38 against 40.
- **Cost:** 4.5× as much.
- **Latency:** 8× slower at p95, 10.17 s against 1.23 s.
- **Where it wins:** only on 4203, which the direct call already gets 10/10, and it fails 4204 and 4206 like every other way.

The same reasoning rules out a hybrid built on the direct call. The direct call fails only 4204 and 4206, and the agent scored 0 on both, so no hand-off rule could add passes. To solve those two issues the tools need to change, not the control flow: something that can read a file, or search results ranked by relevance rather than by path.

**What I would ship: the direct call.** `analysis.verdict` is `workflow`, meaning the control flow stays in my code.

- **Why the direct call:** it has the most passes (40/60), gets the same 4 of 6 right in every sweep, has the lowest p95 latency, and costs $0.0005 per run.
- **Safety:** my code builds its comment, so the worst a bad answer can do is post a wrong two-line label, never free text from the model.
- **When I'd pick the hybrid:** only if the design had to use search.

With the tools this assignment gives, the agent costs more and isn't more accurate.

## Assistance

**AI Tool Used:** Claude Code

I used Claude Code during this assignment. It assisted me in implementing eval/part0.py, agent/loop.py, agent/bounds.yaml. I went through that code and checked that it did what I intended. It also helped me refine the prompts in prompts/, including the development-only tuning of the agent prompt and loop described in Part A. 

For the written work, I wrote the first drafts of reports/PREDICTIONS_01.md, this report, ARCHITECTURE.md and CHANGES.md myself. Claude Code then reviewed them for inconsistencies, clarity and grammar and helped me make them easier to read. I ran make test, make bounds-smoke and make check-01 and confirmed that all three pass. I also verified that the predictions were committed and pushed separately before the first evaluation run, and that no evaluation answer path appears in prompts/, ways/ or agent/. 

Finally, I checked that the numbers in this report match reports/LAB_01.json, which eval/summarize.py generates from the execution traces, and I read the traces cited in Parts C and D to confirm they support what the report states


