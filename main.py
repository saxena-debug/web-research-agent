import argparse
import time
from pathlib import Path
from agent import ResearchAgent
from report import export_html
import config


def print_update(event):
    status = event["status"]
    msg = event["msg"]
    if status == "done":
        print("  v  " + msg)
    elif status == "retry":
        print("  !  " + msg)
    else:
        print("  >  " + msg)


def main():
    parser = argparse.ArgumentParser(description="Research Agent")
    parser.add_argument("goal", type=str, help="Research goal in quotes")
    parser.add_argument("--output", type=str, default=config.REPORT_DIR, help="Dir to save report")
    parser.add_argument("--verbose", action="store_true", help="Sho detailed logs")
    args = parser.parse_args()

    # will override report dir if custom output given
    config.REPORT_DIR = args.output
    Path(args.output).mkdir(parents=True, exist_ok=True)

    print("\nGoal: " + args.goal)
    print("-" * 50)

    agent = ResearchAgent()
    result = agent.run(args.goal, callback=print_update)

    path = export_html(result)

    print(":" * 50)
    print("  Report saved to: " + path)
    print("  Logs saved to:   ./" + config.LOG_DIR + "/")
    print("  Done in " + str(result["total_time"]) + "s\n")


if __name__ == "__main__":
    main()
