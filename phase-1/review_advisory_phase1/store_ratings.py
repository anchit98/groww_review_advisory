"""Fetch public store listing average ratings (not computed from ingested reviews)."""

from __future__ import annotations

import json
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any

from .fetch_real_reviews import GROWW_APP_STORE_ID, GROWW_PLAY_STORE_PACKAGE, FetchError

ITUNES_LOOKUP_URL = "https://itunes.apple.com/lookup?id={app_id}&country={country}"


@dataclass(frozen=True)
class StoreRatingSnapshot:
    source: str
    average_rating: float
    rating_count: int | None
    fetched_at: str
    package_or_app_id: str
    country: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["label"] = "Play Store" if self.source == "play_store" else "App Store"
        return payload


def fetch_play_store_listing_rating(
    *,
    package_name: str = GROWW_PLAY_STORE_PACKAGE,
    country: str = "in",
    language: str = "en",
) -> StoreRatingSnapshot:
    try:
        from google_play_scraper import app
    except ImportError as exc:
        raise FetchError(
            "google-play-scraper is required for Play Store listing ratings."
        ) from exc

    result = app(package_name, lang=language, country=country)
    score = result.get("score")
    if score is None:
        raise FetchError("Play Store listing did not return an average score.")
    rating_count = result.get("ratings")
    return StoreRatingSnapshot(
        source="play_store",
        average_rating=round(float(score), 2),
        rating_count=int(rating_count) if rating_count is not None else None,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        package_or_app_id=package_name,
        country=country,
    )


def fetch_app_store_listing_rating(
    *,
    app_id: str = GROWW_APP_STORE_ID,
    country: str = "in",
) -> StoreRatingSnapshot:
    url = ITUNES_LOOKUP_URL.format(app_id=app_id, country=country)
    request = urllib.request.Request(url, headers={"User-Agent": "ReviewAdvisoryAgent/1.0"})
    try:
        with urllib.request.urlopen(request, timeout=15.0) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as exc:
        raise FetchError(f"App Store lookup failed: {exc}") from exc

    results = payload.get("results") or []
    if not results:
        raise FetchError("App Store lookup returned no results.")

    entry = results[0]
    average = entry.get("averageUserRating")
    if average is None:
        raise FetchError("App Store lookup did not include averageUserRating.")

    count_raw = entry.get("userRatingCount")
    return StoreRatingSnapshot(
        source="app_store",
        average_rating=round(float(average), 2),
        rating_count=int(count_raw) if count_raw is not None else None,
        fetched_at=datetime.now(timezone.utc).isoformat(),
        package_or_app_id=app_id,
        country=country,
    )


def fetch_groww_store_ratings(*, country: str = "in", language: str = "en") -> dict[str, Any]:
    play = fetch_play_store_listing_rating(country=country, language=language)
    app = fetch_app_store_listing_rating(country=country)
    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "country": country,
        "disclaimer": "Overall ratings as shown on each store's public listing (not computed from this pipeline's review sample).",
        "stores": {
            "play_store": play.to_dict(),
            "app_store": app.to_dict(),
        },
    }
