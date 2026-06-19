#!/usr/bin/env python3
"""Run the observed UCI credit-default case study and populate Risk Studio."""
from pathlib import Path
import argparse
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from marvis.credit_case_study import run_case_study  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--offline", action="store_true", help="Require pinned cached UCI archive")
    parser.add_argument("--workspace", type=Path, default=ROOT / "workspace")
    parser.add_argument("--output", type=Path, default=ROOT / "evidence" / "credit-default")
    args = parser.parse_args()
    report = run_case_study(ROOT, offline=args.offline, workspace=args.workspace, output=args.output)
    print(json.dumps({"output": str(args.output), "workspace": str(args.workspace),
                      "rows": report["data_quality"]["rows"], "partitions": report["partitions"],
                      "holdout": {k: v for k, v in report["models"][report["reference_model"]]["holdout"].items() if k != "reliability"}}, indent=2))


if __name__ == "__main__":
    main()
