from __future__ import annotations

import argparse
import os
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./debug-scrape-source.db")
os.environ.setdefault("SECRET_KEY", "debug-scrape-source-secret-key-abcdefghijklmnopqrstuvwxyz")

from bs4 import BeautifulSoup

from backend.services.racing.scrapers.punters_scraper import PuntersScraper


def main() -> None:
    parser = argparse.ArgumentParser(description="Render and inspect a racing scrape source without writing to the database.")
    parser.add_argument("source", choices=["punters"], help="Source to debug. Currently only Punters is implemented.")
    parser.add_argument("--url", default=None, help="Override source URL. Defaults to PUNTERS_SCRAPE_URL or Punters form-guide.")
    parser.add_argument("--date", default=date.today().isoformat(), help="Race date in YYYY-MM-DD format.")
    parser.add_argument("--output-dir", default="debug/punters", help="Directory for rendered HTML snapshots.")
    args = parser.parse_args()

    race_date = date.fromisoformat(args.date)
    scraper = PuntersScraper(start_url=args.url, use_playwright=True)
    url = scraper.build_url(race_date)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"punters_rendered_{race_date.isoformat()}.html"

    html = scraper.fetch_page(url)
    output_path.write_text(html, encoding="utf-8")
    meetings = scraper.parse(html, race_date)
    diagnostics = scraper.build_diagnostics(html, meetings)
    soup = BeautifulSoup(html, "html.parser")

    print(f"source=punters")
    print(f"url={url}")
    print(f"snapshot={output_path}")
    print(f"http_status_code={diagnostics.http_status_code}")
    print(f"page_title={diagnostics.page_title}")
    print(f"tables_found={diagnostics.tables_found}")
    print(f"json_ld_found={diagnostics.json_ld_found}")
    print(f"meetings_parsed={diagnostics.meetings_parsed}")
    print(f"races_parsed={diagnostics.races_parsed}")
    print(f"runners_parsed={diagnostics.runners_parsed}")
    print(f"odds_parsed={diagnostics.odds_parsed}")
    print(f"zero_records_reason={diagnostics.zero_records_reason}")
    print("selectors_used=meeting:h1,h2; races:table,a[href*=race-]; runners:table tbody tr; odds:odds/price/sp columns; results:position/pos/place columns")
    if diagnostics.meetings_parsed == 0:
        body = soup.get_text(" ", strip=True)[:1000]
        print(f"body_sample={body}")


if __name__ == "__main__":
    main()
