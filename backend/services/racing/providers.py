from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Any, Protocol

import httpx

from backend.core.config import settings


class ProviderConfigurationError(RuntimeError):
    pass


class RacingFormProvider(Protocol):
    name: str

    def fetch_meetings(self, race_date: date) -> list[dict[str, Any]]:
        ...

    def fetch_racecard(self, meeting_external_id: str) -> dict[str, Any]:
        ...

    def fetch_results(self, race_date: date) -> list[dict[str, Any]]:
        ...


class OddsProvider(Protocol):
    name: str

    def fetch_odds(self, race_external_id: str | None = None) -> list[dict[str, Any]]:
        ...


def _auth_headers(header_name: str, api_key: str) -> dict[str, str]:
    if header_name.lower() == "authorization" and not api_key.lower().startswith(("bearer ", "basic ")):
        return {header_name: f"Bearer {api_key}"}
    return {header_name: api_key}


def _extract_list(payload: Any, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    for key in keys:
        value = payload.get(key)
        if isinstance(value, list):
            return [item for item in value if isinstance(item, dict)]
    return []


@dataclass
class GenericRacingFormApiProvider:
    base_url: str
    api_key: str
    api_key_header: str = "Authorization"
    meetings_path: str = "/racecards"
    racecard_path: str = "/racecards/{meeting_id}"
    results_path: str = "/results"
    name: str = "generic_http_racing_form"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url.rstrip("/"),
            headers=_auth_headers(self.api_key_header, self.api_key),
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )

    def fetch_meetings(self, race_date: date) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get(self.meetings_path, params={"date": race_date.isoformat()})
            response.raise_for_status()
            return _extract_list(response.json(), ("meetings", "racecards", "data", "items"))

    def fetch_racecard(self, meeting_external_id: str) -> dict[str, Any]:
        path = self.racecard_path.format(meeting_id=meeting_external_id)
        with self._client() as client:
            response = client.get(path)
            response.raise_for_status()
            payload = response.json()
            return payload if isinstance(payload, dict) else {"races": payload}

    def fetch_results(self, race_date: date) -> list[dict[str, Any]]:
        with self._client() as client:
            response = client.get(self.results_path, params={"date": race_date.isoformat()})
            response.raise_for_status()
            return _extract_list(response.json(), ("results", "races", "data", "items"))


@dataclass
class GenericOddsApiProvider:
    base_url: str
    api_key: str
    api_key_header: str = "Authorization"
    markets_path: str = "/odds"
    name: str = "generic_http_odds"

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.base_url.rstrip("/"),
            headers=_auth_headers(self.api_key_header, self.api_key),
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )

    def fetch_odds(self, race_external_id: str | None = None) -> list[dict[str, Any]]:
        params = {"race_id": race_external_id} if race_external_id else None
        with self._client() as client:
            response = client.get(self.markets_path, params=params)
            response.raise_for_status()
            return _extract_list(response.json(), ("odds", "markets", "data", "items"))


def get_racing_form_provider() -> RacingFormProvider:
    if settings.RACING_FORM_PROVIDER != "generic_http":
        raise ProviderConfigurationError(
            f"Unsupported racing form provider '{settings.RACING_FORM_PROVIDER}'. "
            "Add a provider adapter in backend.services.racing.providers."
        )
    if not settings.RACING_FORM_API_BASE_URL or not settings.RACING_FORM_API_KEY:
        raise ProviderConfigurationError(
            "RACING_FORM_API_BASE_URL and RACING_FORM_API_KEY must be set before syncing racing form data."
        )
    return GenericRacingFormApiProvider(
        base_url=settings.RACING_FORM_API_BASE_URL,
        api_key=settings.RACING_FORM_API_KEY,
        api_key_header=settings.RACING_FORM_API_KEY_HEADER,
        meetings_path=settings.RACING_FORM_MEETINGS_PATH,
        racecard_path=settings.RACING_FORM_RACECARD_PATH,
        results_path=settings.RACING_FORM_RESULTS_PATH,
    )


def get_odds_provider() -> OddsProvider:
    if settings.ODDS_PROVIDER != "generic_http":
        raise ProviderConfigurationError(
            f"Unsupported odds provider '{settings.ODDS_PROVIDER}'. "
            "Add a provider adapter in backend.services.racing.providers."
        )
    if not settings.ODDS_API_BASE_URL or not settings.ODDS_API_KEY:
        raise ProviderConfigurationError("ODDS_API_BASE_URL and ODDS_API_KEY must be set before syncing odds.")
    return GenericOddsApiProvider(
        base_url=settings.ODDS_API_BASE_URL,
        api_key=settings.ODDS_API_KEY,
        api_key_header=settings.ODDS_API_KEY_HEADER,
        markets_path=settings.ODDS_MARKETS_PATH,
    )
