from __future__ import annotations

import argparse
from datetime import date

from backend.core.database import Base, SessionLocal, engine
import backend.models  # noqa: F401 - register SQLAlchemy models
from backend.services.racing.scraping_sync import sync_scraping_sources


def main() -> None:
    Base.metadata.create_all(bind=engine)
    parser = argparse.ArgumentParser(description="Collect permitted web-sourced racing data from configured scraper URLs.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Race date in YYYY-MM-DD format.")
    parser.add_argument(
        "--source",
        default="all",
        choices=["all", "tab", "sportsbet", "racing_com", "punters"],
        help="Scraping source to collect. Check robots.txt and terms before use.",
    )
    args = parser.parse_args()
    race_date = date.fromisoformat(args.date)
    db = SessionLocal()
    try:
        runs = sync_scraping_sources(db, race_date, args.source)
        for run in runs:
            print(
                f"{run.provider}: {run.status}; records={run.records_processed}; "
                f"missing={run.missing_data_fields or []}; error={run.error_message or '-'}"
            )
    finally:
        db.close()


if __name__ == "__main__":
    main()
