"""Mappers for the-odds-api.com v4 API responses.

All functions are pure: dict → DTO.

Field mapping
-------------
the-odds-api.com uses string IDs (hex strings).
We store them as-is, prefixed with "oddsapi." for namespace clarity.

Market mapping
--------------
    h2h   → OddsMarket.MATCH_WINNER  (1X2 head-to-head)
    totals → OddsMarket.OVER_UNDER

Selection mapping for h2h
-------------------------
The outcomes list has three entries: home_team name, away_team name, "Draw".
We map them to SelectionType.HOME / AWAY / DRAW by matching outcome name
against the event's home_team and away_team fields.
"""
from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal
from typing import Any

from athena.db.enums import OddsMarket, SelectionType
from athena.providers.models import OddsSelectionDTO, OddsSnapshotDTO

# ── Market mapping ────────────────────────────────────────────────────────────

_MARKET_MAP: dict[str, OddsMarket] = {
    "h2h": OddsMarket.MATCH_WINNER,
    "totals": OddsMarket.OVER_UNDER,
    "btts": OddsMarket.BTTS,
}


# ── Public mapper functions ───────────────────────────────────────────────────

def map_odds_event(raw: dict[str, Any]) -> list[OddsSnapshotDTO]:
    """Map one event (match) from the-odds-api.com response to a list of snapshots.

    Each bookmaker × market combination becomes one ``OddsSnapshotDTO``.

    Args:
        raw: One entry from the top-level list returned by the API.

    Returns:
        List of ``OddsSnapshotDTO``, one per bookmaker per market.
    """
    match_external_id = f"oddsapi.{raw['id']}"
    home_team = raw.get("home_team", "")
    away_team = raw.get("away_team", "")
    commence_time_str = raw.get("commence_time", "")
    parsed_captured_at = _parse_utc(commence_time_str)
    # Last-resort fallback: if the event itself has no parsable commence_time,
    # fall back to "now" rather than propagate None into a non-optional field.
    captured_at: datetime = parsed_captured_at or datetime.now(timezone.utc)

    snapshots: list[OddsSnapshotDTO] = []

    for bookmaker in raw.get("bookmakers", []):
        bk_slug = bookmaker.get("key", "unknown")
        bk_name = bookmaker.get("title", bk_slug)
        bk_update_str = bookmaker.get("last_update", commence_time_str)
        bk_captured_at: datetime = _parse_utc(bk_update_str) or captured_at

        for market in bookmaker.get("markets", []):
            market_key = market.get("key", "")
            odds_market = _MARKET_MAP.get(market_key)
            if odds_market is None:
                continue  # skip unsupported markets silently

            market_update_str = market.get("last_update", bk_update_str)
            market_captured_at: datetime = _parse_utc(market_update_str) or bk_captured_at

            selections = _map_selections(
                market.get("outcomes", []),
                home_team=home_team,
                away_team=away_team,
                market_key=market_key,
            )

            snapshots.append(
                OddsSnapshotDTO(
                    match_external_id=match_external_id,
                    bookmaker_slug=bk_slug,
                    bookmaker_name=bk_name,
                    market=odds_market,
                    captured_at=market_captured_at,
                    source="odds-api",
                    selections=tuple(selections),
                    is_closing=False,
                    external_ref=f"oddsapi.{raw['id']}.{bk_slug}.{market_key}",
                )
            )

    return snapshots


def map_odds_response(raw: list[dict[str, Any]]) -> list[OddsSnapshotDTO]:
    """Map the full odds API response (a list of events).

    Args:
        raw: Top-level list from the API.
    """
    result: list[OddsSnapshotDTO] = []
    for event in raw:
        result.extend(map_odds_event(event))
    return result


# ── Private helpers ───────────────────────────────────────────────────────────

def _parse_utc(dt_str: str) -> datetime | None:
    """Parse an ISO 8601 UTC string, returning None on failure."""
    if not dt_str:
        return None
    try:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except (ValueError, AttributeError):
        return None


def _map_selections(
    outcomes: list[dict[str, Any]],
    *,
    home_team: str,
    away_team: str,
    market_key: str,
) -> list[OddsSelectionDTO]:
    """Convert outcome dicts to OddsSelectionDTO list."""
    selections: list[OddsSelectionDTO] = []
    for outcome in outcomes:
        name = outcome.get("name", "")
        price = outcome.get("price")
        if price is None:
            continue

        decimal_odd = Decimal(str(price))
        selection_type = _infer_selection_type(name, home_team, away_team)

        selections.append(
            OddsSelectionDTO(
                selection_type=selection_type,
                decimal_odd=decimal_odd,
                label=name if selection_type not in (
                    SelectionType.HOME, SelectionType.DRAW, SelectionType.AWAY
                ) else None,
            )
        )
    return selections


def _infer_selection_type(
    name: str,
    home_team: str,
    away_team: str,
) -> SelectionType:
    """Infer SelectionType from outcome name and team names."""
    if name == "Draw":
        return SelectionType.DRAW
    if name == home_team:
        return SelectionType.HOME
    if name == away_team:
        return SelectionType.AWAY
    # Fallback: Over/Under or unknown
    lower = name.lower()
    if "over" in lower:
        return SelectionType.OVER
    if "under" in lower:
        return SelectionType.UNDER
    # Generic fallback — label will carry the name
    return SelectionType.HOME
