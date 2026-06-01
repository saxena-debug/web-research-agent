import subprocess
import csv
import sys
import os
import re
from datetime import datetime

result = subprocess.run(
    [sys.executable, "-m", "pytest", "tests/test_core.py", "-v", "--tb=short"],
    capture_output=True,
    text=True,
    cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
)

print(result.stdout)
if result.stderr:
    print(result.stderr)

# it iwll parse only lines like: tests/test_core.py::test_name PASSED
rows = []
timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
pattern = re.compile(r'^(tests/\S+)::(\S+)\s+(PASSED|FAILED|ERROR)')
for line in result.stdout.splitlines():
    m = pattern.match(line.strip())
    if m:
        rows.append({
            "timestamp": timestamp,
            "file":      m.group(1),
            "test":      m.group(2),
            "status":    m.group(3),
        })

os.makedirs("tests/results", exist_ok=True)
csv_path = "tests/results/test_results.csv"
write_header = not os.path.exists(csv_path)
with open(csv_path, "a", newline="") as f:
    writer = csv.DictWriter(f, fieldnames=["timestamp", "file", "test", "status"])
    if write_header:
        writer.writeheader()
    writer.writerows(rows)

#print(len(rows))
passed = sum(1 for r in rows if r["status"] == "PASSED")
print("Results saved to " + csv_path + "  (" + str(passed) + "/" + str(len(rows)) + " passed)")
sys.exit(result.returncode)
