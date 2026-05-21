"""Public store listing average ratings (Play Store + App Store)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import repo_root

GROWW_PLAY_STORE_PACKAGE = "com.nextbillion.groww"
GROWW_APP_STORE_ID = "1404871703"
ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup?id={app_id}&country={country}"


def _fetch_play_store(*, country: str = "in", language: str = "en") -> dict[str, Any]:
    from google_play_scraper import app

    result = app(GROWW_PLAY_STORE_PACKAGE, lang=language, country=country)
    score = result.get("score")
    if score is None:
        raise RuntimeError("Play Store listing did not return an average score.")
    count = result.get("ratings")
    return {
        "source": "play_store",
        "label": "Play Store",
        "average_rating": round(float(score), 2),
        "rating_count": int(count) if count is not None else None,
        "package_or_app_id": GROWW_PLAY_STORE_PACKAGE,
        "country": country,
    }


def _fetch_app_store(*, country: str = "in") -> dict[str, Any]:
    url = ITUNES_LOOKUP_URL.format(app_id=GROWW_APP_STORE_ID, country=country)
    request = urllib.request.Request(url, headers={"User-Agent": "ReviewAdvisoryAgent/1.0"})
    with urllib.request.urlopen(request, timeout=15.0) as response:
        payload = json.loads(response.read().decode("utf-8"))
    results = payload.get("results") or []
    if not results:
        raise RuntimeError("App Store lookup returned no results.")
    entry = results[0]
    average = entry.get("averageUserRating")
    if average is None:
        raise RuntimeError("App Store lookup did not include averageUserRating.")
    count_raw = entry.get("userRatingCount")
    return {
        "source": "app_store",
        "label": "App Store",
        "average_rating": round(float(average), 2),
        "rating_count": int(count_raw) if count_raw is not None else None,
        "package_or_app_id": GROWW_APP_STORE_ID,
        "country": country,
    }


def fetch_live_listing_ratings(*, country: str = "in", language: str = "en") -> dict[str, Any]:
    play = _fetch_play_store(country=country, language=language)
    app = _fetch_app_store(country=country)
    now = datetime.now(timezone.utc).isoformat()
    play["fetched_at"] = now
    app["fetched_at"] = now
    return {
        "fetched_at": now,
        "country": country,
        "disclaimer": "Overall ratings as shown on each store's public listing (not computed from this pipeline's review sample).",
        "stores": {
            "play_store": play,
            "app_store": app,
        },
    }


def listing_ratings_path() -> Path:
    return repo_root() / "data" / "store_ratings.json"


def load_listing_ratings(*, refresh_if_missing: bool = True) -> dict[str, Any] | None:
    path = listing_ratings_path()
    if path.exists():
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict) and payload.get("stores"):
            return payload

    if not refresh_if_missing:
        return None

    try:
        payload = fetch_live_listing_ratings()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return payload
    except Exception:
        return None
