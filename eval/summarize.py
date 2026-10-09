"""Assignment 1, Parts B to D: build the tables in reports/LAB_01.json from your runs. This file is yours.

Read every trace in runs/ and the comments in the tracker, decide each run's
success with eval/check_triage.check, and compute the `results` entry for each
way (direct, workflow, agent, hybrid) and the computed fields of `analysis`.
Write them into reports/LAB_01.json and leave every other field (part0,
verdict) as you set it. Every field is defined in checks/FORMATS.md, section 7.

    python -m eval.summarize            # write results, analysis and the measured worst case
    python -m eval.summarize --print    # also print a Markdown table of the results
"""

from __future__ import annotations

import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import yaml

from agent.loop import load_bounds
from eval.check_triage import check
from harness.trace import read_trace
from harness.tracker import Tracker

ROOT = Path(__file__).resolve().parent.parent
REPORT = ROOT / "reports" / "LAB_01.json"
WAYS = ("direct", "workflow", "agent", "hybrid")
RUNS_PER_ISSUE = 10
SCRIPTED = {"never-stops"}


def load_answers() -> dict[int, dict]:
    data = yaml.safe_load((ROOT / "fixtures" / "answers.yaml").read_text())["eval"]
    return {int(k): v for k, v in data.items()}


def load_runs(issues: set[int]) -> dict[str, list[dict]]:
    """Every finished evaluation run of every way, from its trace."""
    runs: dict[str, list[dict]] = {w: [] for w in WAYS}
    for path in sorted((ROOT / "runs").glob("*.jsonl")):
        if path.name.startswith("_"):
            continue
        records = read_trace(path)
        if not records or records[0]["type"] != "run_start" or records[-1]["type"] != "run_end":
            continue
        start, end = records[0], records[-1]
        if (start.get("lab") != "01" or start.get("way") not in WAYS
                or start.get("backend") in SCRIPTED or start.get("issue") not in issues):
            continue
        ends = [r for r in records if r["type"] == "end"]
        runs[start["way"]].append({
            "run_id": start["run_id"], "issue": start["issue"], "sweep": start["sweep"],
            "model_calls": [r for r in records if r["type"] == "model_call"],
            "tool_calls": [r for r in records if r["type"] == "tool_call"],
            "terminal_reason": ends[-1]["terminal_reason"] if ends else None,
            "elapsed_s": end["elapsed_s"],
        })
    return runs


def mean(values):
    return sum(values) / len(values) if values else None


def nearest_rank(values, pct):
    """Nearest-rank percentile: the smallest value with at least pct% of values at or below it."""
    if not values:
        return None
    ordered = sorted(values)
    return ordered[max(1, math.ceil(pct / 100 * len(ordered))) - 1]


def way_results(runs: list[dict], passed: dict[str, bool], issues: list[int]) -> dict:
    per_issue_runs, per_issue_pass, per_sweep = defaultdict(int), defaultdict(int), defaultdict(int)
    for r in runs:
        ok = passed[r["run_id"]]
        per_issue_runs[r["issue"]] += 1
        per_issue_pass[r["issue"]] += ok
        per_sweep[r["sweep"]] += ok
    sweeps = sorted({r["sweep"] for r in runs})

    def summed(r, key):
        return sum(c["usage"][key] for c in r["model_calls"])

    tool_counts = [len(r["tool_calls"]) for r in runs]
    elapsed = [r["elapsed_s"] for r in runs]
    return {
        "runs": len(runs),
        "passes": sum(passed[r["run_id"]] for r in runs),
        "per_issue": {str(i): per_issue_pass[i] for i in issues},
        "sweep_min": min((per_sweep[s] for s in sweeps), default=None),
        "sweep_max": max((per_sweep[s] for s in sweeps), default=None),
        "all_ten": sum(1 for i in issues
                       if per_issue_runs[i] >= RUNS_PER_ISSUE and per_issue_pass[i] == per_issue_runs[i]),
        "mean_prompt_tokens": mean([summed(r, "prompt_tokens") for r in runs]),
        "mean_output_tokens": mean([summed(r, "output_tokens") for r in runs]),
        "mean_cached_tokens": mean([summed(r, "cache_read_input_tokens") for r in runs]),
        "p50_latency_s": nearest_rank(elapsed, 50),
        "p95_latency_s": nearest_rank(elapsed, 95),
        "mean_cost_usd": mean([sum(c["cost_usd"] or 0 for c in r["model_calls"]) for r in runs]),
        "mean_tool_calls": mean(tool_counts),
        "max_tool_calls": max(tool_counts, default=None),
    }


def measured_worst_case(agent_runs: list[dict]) -> dict | None:
    """F and A measured on the agent's evaluation runs (checks/FORMATS.md, section 4)."""
    firsts, deltas = [], []
    for r in agent_runs:
        prompts = [c["usage"]["prompt_tokens"] for c in r["model_calls"]]
        if prompts:
            firsts.append(prompts[0])
        deltas += [b - a for a, b in zip(prompts, prompts[1:])]
    if not firsts or not deltas:
        return None
    n = load_bounds().max_steps
    f, a = round(mean(firsts), 1), round(mean(deltas), 1)
    return {"F": f, "A": a, "N": n, "cumulative_prompt_tokens": round(n * f + a * n * (n - 1) / 2, 1)}


def analysis(results: dict, runs: dict) -> dict:
    out = {}
    direct, workflow, agent = results["direct"], results["workflow"], results["agent"]

    def tokens(r):
        return (r["mean_prompt_tokens"] or 0) + (r["mean_output_tokens"] or 0)

    if direct["runs"] and agent["runs"]:
        out["ratio_agent_over_direct_tokens"] = round(tokens(agent) / tokens(direct), 3)
    if workflow["runs"] and agent["runs"]:
        c = workflow["mean_cost_usd"]
        m = agent["mean_cost_usd"] / c
        issues = list(workflow["per_issue"])
        earns = [i for i in issues if workflow["per_issue"][i] < 5 and agent["per_issue"][i] >= 5]
        f = len(earns) / len(issues)
        out.update({
            "m_agent_over_workflow_cost": round(m, 3),
            "f": round(f, 4),
            "blended_cost": c * ((1 - f) + f * m),
            "all_agent_cost": c * m,
            "workflow_cost": c,
        })
    if runs["agent"]:
        sequences = Counter(tuple(t["name"] for t in r["tool_calls"]) for r in runs["agent"])
        top3 = sum(n for _, n in sequences.most_common(3))
        out["path_entropy"] = {"distinct_sequences": len(sequences),
                               "top3_share": round(top3 / len(runs["agent"]), 4)}
    if runs["hybrid"]:
        out["hybrid_handoffs"] = sum(1 for r in runs["hybrid"] if r["terminal_reason"] != "completed")
    return out


def table(results: dict) -> str:
    issues = list(results["direct"]["per_issue"])
    head = ["Measure"] + [w for w in WAYS if results[w].get("runs")]
    rows = [("Passes / runs", lambda r: f"{r['passes']} / {r['runs']}")]
    rows += [(f"#{i} passes / 10", lambda r, i=i: str(r["per_issue"][i])) for i in issues]
    rows += [
        ("Sweep min-max", lambda r: f"{r['sweep_min']}-{r['sweep_max']}"),
        ("Issues 10/10", lambda r: str(r["all_ten"])),
        ("Mean prompt tok", lambda r: f"{r['mean_prompt_tokens']:,.0f}"),
        ("  of which cached", lambda r: f"{r['mean_cached_tokens']:,.0f}"),
        ("Mean output tok", lambda r: f"{r['mean_output_tokens']:,.0f}"),
        ("p50 / p95 latency (s)", lambda r: f"{r['p50_latency_s']:.2f} / {r['p95_latency_s']:.2f}"),
        ("Mean cost ($)", lambda r: f"{r['mean_cost_usd']:.6f}"),
        ("Tool calls mean / max", lambda r: f"{r['mean_tool_calls']:.2f} / {r['max_tool_calls']}"),
    ]
    lines = ["| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
    for name, fmt in rows:
        lines.append("| " + " | ".join([name] + [fmt(results[w]) for w in head[1:]]) + " |")
    return "\n".join(lines)


def main(argv: list[str]) -> None:
    answers = load_answers()
    issues = sorted(answers)
    tracker = Tracker(ROOT)
    runs = load_runs(set(issues))
    passed = {r["run_id"]: check(tracker, r["run_id"], r["issue"], answers[r["issue"]])
              for way in WAYS for r in runs[way]}

    report = json.loads(REPORT.read_text())
    for way in WAYS:
        if runs[way]:
            report["results"][way] = way_results(runs[way], passed, issues)
    report["analysis"].update(analysis(report["results"], runs))
    worst = measured_worst_case(runs["agent"])
    if worst:
        report["worst_case"] = worst
    REPORT.write_text(json.dumps(report, indent=2) + "\n")

    print(f"wrote {REPORT.relative_to(ROOT)}: " + ", ".join(f"{w} {len(runs[w])} runs" for w in WAYS))
    if "--print" in argv:
        print()
        print(table(report["results"]))
        print()
        print(json.dumps({"worst_case": report["worst_case"], "analysis": report["analysis"]}, indent=2))


if __name__ == "__main__":
    main(sys.argv[1:])
