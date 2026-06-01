'''
I am evluating the logs to generate the performance report
'''

import csv
import sys
import os
from datetime import datetime
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import config

LOGS_DIR    = Path(config.LOG_DIR)
RESULTS_DIR = Path(__file__).parent / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

PIPELINE_ORDER = [
    "query_expansion",
    "web_search",
    "summarize_sources",
    "quality_check",
    "compile_report",
]


def read_runs():
    path = LOGS_DIR / "agent_runs.csv"
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def read_tasks():
    path = LOGS_DIR / "task_events.csv"
    if not path.exists():
        return []
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def tasks_for_run(run_id, all_tasks):
    return [t for t in all_tasks if t["run_id"] == run_id]


def compute_latency(tasks):
    breakdown = {}
    for t in tasks:
        task = t["task"]
        try:
            ms = int(t["duration_ms"])
        except (ValueError, KeyError):
            ms = 0
        if task in PIPELINE_ORDER:
            breakdown[task] = breakdown.get(task, 0) + ms
    total = sum(breakdown.values())
    return breakdown, total


def check_tool_order(tasks):
    seen = []
    for t in tasks:
        if t["task"] in PIPELINE_ORDER and t["task"] not in seen:
            seen.append(t["task"])
    expected = [s for s in PIPELINE_ORDER if s in seen]
    return seen == expected, seen


def retry_count(tasks):
    return len([t for t in tasks if t.get("status") == "retry"])


def quality_score(tasks):
    scores = []
    for t in tasks:
        if t["task"] == "quality_check":
            try:
                scores.append(float(t["score"]))
            except (ValueError, KeyError):
                pass
    return max(scores) if scores else 0.0


def run_time_seconds(run):
    try:
        start = datetime.fromisoformat(run["start_time"])
        end   = datetime.fromisoformat(run["end_time"])
        return round((end - start).total_seconds(), 1)
    except Exception:
        return 0.0


def save_report(runs, all_tasks):
    timestamp = datetime.now().strftime("%Y-%m-%dT%H-%M-%S")
    csv_rows = []

    print(len(runs))
    print(len(all_tasks))

    for run in runs:
        run_id  = run["run_id"]
        status  = run["status"]
        tokens  = run.get("tokens_used", "0")
        elapsed = run_time_seconds(run)

        tasks             = tasks_for_run(run_id, all_tasks)
        latency, total_ms = compute_latency(tasks)
        order_ok, _       = check_tool_order(tasks)
        retries           = retry_count(tasks)
        score             = quality_score(tasks)

        csv_rows.append({
            "run_id":               run_id,
            "goal":                 run["goal"],
            "status":               status,
            "wall_time_s":          elapsed,
            "total_tokens":         tokens,
            "quality_score":        "%.2f" % score,
            "retries":              retries,
            "tool_order_valid":     order_ok,
            "query_expansion_ms":   latency.get("query_expansion", 0),
            "web_search_ms":        latency.get("web_search", 0),
            "summarize_sources_ms": latency.get("summarize_sources", 0),
            "quality_check_ms":     latency.get("quality_check", 0),
            "compile_report_ms":    latency.get("compile_report", 0),
            "total_pipeline_ms":    total_ms,
        })

    if not csv_rows:
        return None

    print(len(csv_rows))

    csv_path = RESULTS_DIR / ("performance_" + timestamp + ".csv")

    with open(csv_path, "w+", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=csv_rows[0].keys())
        writer.writeheader()
        writer.writerows(csv_rows)

    return str(csv_path)


if __name__ == "__main__":
    runs      = read_runs()
    all_tasks = read_tasks()

    #report created only on finished tasks
    finished  = [r for r in runs if r["status"] not in ("running",)]


    if not finished:
        sys.exit(0)

    save_report(finished, all_tasks)


#CHECK it now, TODO: add to readme later

#next additions could be:
#python eval/performance_report.py          # last 5 runs
#python eval/performance_report.py --n 10   # last 10 runs
#python eval/performance_report.py --all    # all runs ever