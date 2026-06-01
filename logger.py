import csv
import json
import os
from datetime import datetime
from pathlib import Path
import config


class AgentLogger:
    def __init__(self, run_id):
        self.run_id  = run_id
        self.log_dir = Path(config.LOG_DIR)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self._init_csv("agent_runs.csv",  ["run_id", "goal", "status", "start_time", "end_time", "tokens_used"])
        self._init_csv("task_events.csv", ["run_id", "task", "status", "score", "reason", "duration_ms", "timestamp"])

    def _init_csv(self, filename, headers):
        path = self.log_dir / filename
        if not path.exists():
            with open(path, "w", newline="") as f:
                csv.writer(f).writerow(headers)

    def _append_csv(self, filename, row):
        with open(self.log_dir / filename, "a", newline="") as f:
            csv.writer(f).writerow(row)

    def log_run_start(self, goal):
        self._append_csv("agent_runs.csv", [
            self.run_id, goal, "running", datetime.now().isoformat(), "", ""
        ])

    def log_run_end(self, status, tokens_used=0):
        # read the whole file, find our row, update in place, write back.
        # a bit clunky but avoids adding a db dependency for whats essentially
        # a single row update per run.
        path = self.log_dir / "agent_runs.csv"
        with open(path, "r", newline="") as f:
            rows = list(csv.reader(f))

        for i, row in enumerate(rows):
            if i == 0:
                continue
            if not row or not row[0]:
                continue
            if row[0] == self.run_id:
                row[2] = status
                row[4] = datetime.now().isoformat()
                row[5] = str(tokens_used)
                break

        with open(path, "w", newline="") as f:
            csv.writer(f).writerows(rows)

    def log_task(self, task, status, score="", reason="", duration_ms=0):
        self._append_csv("task_events.csv", [
            self.run_id, task, status, score, reason,
            duration_ms, datetime.now().isoformat()
        ])

    def log_llm_trace(self, step, user_prompt, response, tokens=0):
        trace = {
            "run_id":    self.run_id,
            "step":      step,
            "timestamp": datetime.now().isoformat(),
            "tokens":    tokens,
            "user":      user_prompt,
            "response":  response,
        }
        with open(self.log_dir / "llm_traces.jsonl", "a") as f:
            f.write(json.dumps(trace) + "\n")
