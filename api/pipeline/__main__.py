import argparse
import json
import logging
from pathlib import Path

from api.pipeline.transactions import run_pipeline

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    parser = argparse.ArgumentParser(description="Validate, clean, and score FinSight transactions")
    parser.add_argument("--input", default=str(ROOT / "data/raw/transactions.csv"))
    parser.add_argument("--output", default=str(ROOT / "data/processed/transactions_with_anomalies.csv"))
    parser.add_argument("--report", default=str(ROOT / "data/processed/pipeline_summary.json"))
    parser.add_argument("--customers", default=str(ROOT / "data/raw/customers.csv"))
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--contamination", type=float, default=.05)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        summary = run_pipeline(args.input, args.output, args.report, args.customers, args.seed, args.contamination)
        print(json.dumps(summary, indent=2, default=str))
    except (ValueError, OSError) as exc:
        parser.error(str(exc))


if __name__ == "__main__":
    main()
