"""Template for a real racing data provider adapter.

TODO when provider docs/API access are available:
1. Confirm authentication scheme and required request headers.
2. Map racecard endpoints to meetings, races, runners, jockeys, trainers,
   barriers, weights, past form, track conditions, and scratchings.
3. Map results endpoints to race IDs, runner IDs/names, finishing position,
   margins, and starting prices.
4. Map odds endpoints to race IDs, runner IDs/names, bookmaker, decimal odds,
   market type, timestamp, and market movement.
5. Add provider-specific tests using sanitized sample payloads.

Do not fake tips or fabricate race data here. If a required provider field is
missing, return the payload as-is and let the sync layer mark the record as
"insufficient data".
"""

from __future__ import annotations

from datetime import date
from typing import Any


class RacingProviderTodoAdapter:
    name = "provider_todo"

    def fetch_meetings(self, race_date: date) -> list[dict[str, Any]]:
        raise NotImplementedError("Plug in the racing form provider's meetings endpoint shape.")

    def fetch_racecard(self, meeting_external_id: str) -> dict[str, Any]:
        raise NotImplementedError("Plug in the racing form provider's racecard endpoint shape.")

    def fetch_results(self, race_date: date) -> list[dict[str, Any]]:
        raise NotImplementedError("Plug in the racing form provider's results endpoint shape.")


class OddsProviderTodoAdapter:
    name = "odds_provider_todo"

    def fetch_odds(self, race_external_id: str | None = None) -> list[dict[str, Any]]:
        raise NotImplementedError("Plug in the odds provider's market endpoint shape.")
