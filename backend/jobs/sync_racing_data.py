from __future__ import annotations

import argparse
from datetime import date

from backend.core.database import Base, SessionLocal, engine
import backend.models  # noqa: F401 - register SQLAlchemy models
from backend.services.racing.sync import sync_all, sync_odds, sync_racecards, sync_results


def main() -> None:
    Base.metadata.create_all(bind=engine)
    parser = argparse.ArgumentParser(description="Sync racing form, odds, and results from configured APIs.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Race date to sync in YYYY-MM-DD format.")
    parser.add_argument(
        "--sync",
        default="all",
        choices=["all", "racecards", "odds", "results"],
        help="Data set to sync. Intended for cron execution.",
    )
    args = parser.parse_args()
    race_date = date.fromisoformat(args.date)

    db = SessionLocal()
    try:
        if args.sync == "all":
            runs = sync_all(db, race_date)
        elif args.sync == "racecards":
            runs = [sync_racecards(db, race_date)]
        elif args.sync == "odds":
            runs = [sync_odds(db)]
        else:
            runs = [sync_results(db, race_date)]

        for run in runs:
            print(
                f"{run.sync_type}: {run.status}; "
                f"records={run.records_processed}; missing={run.missing_data_fields or []}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
