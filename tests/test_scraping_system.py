import os
from datetime import date
from pathlib import Path

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_scraping_system.db")
os.environ.setdefault("SECRET_KEY", "local-test-secret-key-abcdefghijklmnopqrstuvwxyz")
os.environ.setdefault("ADMIN_API_TOKEN", "test-admin-token")
os.environ.setdefault("CORS_ORIGINS", "http://localhost:3000")

from backend.core.database import Base, SessionLocal, engine
import backend.models  # noqa: F401 - register SQLAlchemy models
from backend.models.racing import Meeting, ModelRating, OddsSnapshot, Race, Runner, SyncRun
from backend.services.racing.scrapers.base_scraper import BaseRacingScraper, ScrapeConfig
from backend.services.racing.scraping_sync import sync_scraper
from backend.services.racing.scrapers.punters_scraper import PuntersScraper


HEADER_FIXTURE_HTML = """
<html><head><title>Header Fixture</title></head><body>
<h1>Header Park</h1>
<table>
  <thead><tr><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Fixed Odds</th></tr></thead>
  <tbody>
    <tr><td>Runner</td><td>Barrier</td><td>Jockey</td><td>Trainer</td><td>Weight</td><td>Fixed Odds</td></tr>
    <tr><td>Fast Comet</td><td>2</td><td>J Smith</td><td>A Trainer</td><td>56.5</td><td>3.20</td></tr>
  </tbody>
</table>
<table>
  <thead><tr><th>Horse</th><th>Draw</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Odds</th></tr></thead>
  <tbody>
    <tr><td>Horse</td><td>Draw</td><td>Jockey</td><td>Trainer</td><td>Weight</td><td>Odds</td></tr>
    <tr><td>River Queen</td><td>7</td><td>L Jones</td><td>B Stable</td><td>58.0</td><td>4.60</td></tr>
  </tbody>
</table>
<table>
  <thead><tr><th>Name</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Price</th></tr></thead>
  <tbody>
    <tr><td>Name</td><td>Barrier</td><td>Jockey</td><td>Trainer</td><td>Weight</td><td>Price</td></tr>
    <tr><td>Golden Mile</td><td>4</td><td>P Lane</td><td>C Yard</td><td>57.0</td><td>5.50</td></tr>
  </tbody>
</table>
</body></html>
"""

SYNC_FIXTURE_HTML = """
<html><head><title>Fixture Racecard</title></head><body>
<h1>Fixture Park</h1>
<table>
  <thead><tr><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Fixed Odds</th></tr></thead>
  <tbody>
    <tr><td>Runner</td><td>Barrier</td><td>Jockey</td><td>Trainer</td><td>Weight</td><td>Fixed Odds</td></tr>
    <tr><td>Fast Comet</td><td>2</td><td>J Smith</td><td>A Trainer</td><td>56.5</td><td>3.20</td></tr>
    <tr><td>River Queen</td><td>7</td><td>L Jones</td><td>B Stable</td><td>58.0</td><td>4.60</td></tr>
  </tbody>
</table>
</body></html>
"""


class FixtureScraper(BaseRacingScraper):
    source_name = "fixture"

    def __init__(self, html: str):
        super().__init__(ScrapeConfig(source_name=self.source_name, start_url="https://fixture.test", rate_limit_seconds=0))
        self.html = html

    def fetch_page(self, url: str) -> str:
        self._last_http_status_code = 200
        self._last_used_playwright = False
        return self.html


def setup_function():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    db_path = Path("test_scraping_system.db")
    if db_path.exists():
        db_path.unlink()


def test_parse_tables_ignores_runner_horse_and_name_header_rows():
    scraper = FixtureScraper(HEADER_FIXTURE_HTML)
    result = scraper.scrape(date(2026, 6, 1))

    runner_names = [runner.horse_name for meeting in result.meetings for race in meeting.races for runner in race.runners]

    assert "Runner" not in runner_names
    assert "Horse" not in runner_names
    assert "Name" not in runner_names
    assert runner_names == ["Fast Comet", "River Queen", "Golden Mile"]
    assert result.diagnostics.tables_found == 3
    assert result.diagnostics.runners_parsed == 3
    assert result.diagnostics.odds_parsed == 3


def test_scraping_sync_saves_structured_data_prevents_duplicate_odds_and_calculates_ratings():
    db = SessionLocal()
    try:
        scraper = FixtureScraper(SYNC_FIXTURE_HTML)
        first_run = sync_scraper(db, scraper, date(2026, 6, 1))
        second_run = sync_scraper(db, scraper, date(2026, 6, 1))

        assert first_run.status == "completed"
        assert second_run.status == "completed"
        assert db.query(Meeting).count() == 1
        assert db.query(Race).count() == 1
        assert db.query(Runner).count() == 2
        assert db.query(OddsSnapshot).count() == 2
        assert db.query(SyncRun).count() == 2

        meeting = db.query(Meeting).one()
        assert meeting.track_name == "Fixture Park"
        assert meeting.data_source == "web_sourced"

        runner_names = [runner.horse_name for runner in db.query(Runner).order_by(Runner.id).all()]
        assert runner_names == ["Fast Comet", "River Queen"]

        odds = db.query(OddsSnapshot).order_by(OddsSnapshot.id).all()
        assert [float(item.odds_decimal) for item in odds] == [3.2, 4.6]

        ratings = db.query(ModelRating).order_by(ModelRating.id).all()
        assert len(ratings) == 2
        assert all(rating.bookmaker_odds is not None for rating in ratings)
        assert all(rating.expected_value is not None for rating in ratings)
        assert all(rating.confidence_label != "insufficient data" for rating in ratings)
        assert all(rating.suggested_staking_unit is not None for rating in ratings)

        latest_log = db.query(SyncRun).order_by(SyncRun.id.desc()).first()
        diagnostics = latest_log.metadata_json["scrape_diagnostics"]
        assert diagnostics["http_status_code"] == 200
        assert diagnostics["page_title"] == "Fixture Racecard"
        assert diagnostics["tables_found"] == 1
        assert diagnostics["runners_parsed"] == 2
        assert diagnostics["odds_parsed"] == 2
    finally:
        db.close()



def test_punters_parser_extracts_source_specific_form_table_without_header_rows():
    html = """
    <html><head><title>Fixture Racecard</title></head><body>
    <h1>Fixture Park Races</h1>
    <h2>Fixture Park, VIC</h2>
    <h3>R3 Fixture Cup 3:20pm</h3>
    <table>
      <thead><tr><th>Runner</th><th>Barrier</th><th>Jockey</th><th>Trainer</th><th>Weight</th><th>Odds</th></tr></thead>
      <tbody>
        <tr><td>Runner</td><td>Barrier</td><td>Jockey</td><td>Trainer</td><td>Weight</td><td>Odds</td></tr>
        <tr><td>Fast Comet</td><td>2</td><td>J Smith</td><td>A Trainer</td><td>56.5</td><td>3.20</td></tr>
        <tr><td>River Queen</td><td>7</td><td>L Jones</td><td>B Stable</td><td>58.0</td><td>4.60</td></tr>
      </tbody>
    </table>
    </body></html>
    """
    scraper = PuntersScraper(start_url="https://fixture.test", use_playwright=False)
    meetings = scraper.parse(html, date(2026, 6, 1))

    assert len(meetings) == 1
    assert meetings[0].track_name == "Fixture Park"
    assert len(meetings[0].races) == 1
    race = meetings[0].races[0]
    assert race.race_number == 3
    assert race.name == "Fixture Cup"
    assert [runner.horse_name for runner in race.runners] == ["Fast Comet", "River Queen"]
    assert [float(odds.odds_decimal) for odds in race.odds] == [3.2, 4.6]
