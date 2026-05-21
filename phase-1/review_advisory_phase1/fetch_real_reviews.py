from __future__ import annotations

import argparse
import csv
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterable


GROWW_APP_STORE_ID = "1404871703"
GROWW_PLAY_STORE_PACKAGE = "com.nextbillion.groww"
DEFAULT_COUNTRY = "in"
DEFAULT_LANGUAGE = "en"
DEFAULT_LOOKBACK_WEEKS = 8
APP_STORE_PAGE_LIMIT = 10
APP_STORE_BASE_URL = (
    "https://itunes.apple.com/{country}/rss/customerreviews/"
    "page={page}/id={app_id}/sortby=mostrecent/json"
)
APP_STORE_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PLAY_STORE_BATCH_SIZE = 200
PLAY_STORE_MAX_BATCHES = 25


class FetchError(RuntimeError):
    pass


def fetch_app_store_reviews(
    *,
    app_id: str,
    country: str,
    cutoff_date: date,
    page_limit: int = APP_STORE_PAGE_LIMIT,
    request_timeout: float = 15.0,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    notes: list[str] = []
    all_records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    stop_due_to_window = False

    for page in range(1, page_limit + 1):
        url = APP_STORE_BASE_URL.format(country=country, page=page, app_id=app_id)
        request = urllib.request.Request(url, headers={"User-Agent": APP_STORE_USER_AGENT})

        try:
            with urllib.request.urlopen(request, timeout=request_timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            notes.append(f"App Store page {page} returned HTTP {exc.code}; stopping pagination.")
            break
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            notes.append(f"App Store page {page} failed: {exc}. Stopping pagination.")
            break

        entries = (payload.get("feed") or {}).get("entry") or []
        if isinstance(entries, dict):
            entries = [entries]

        if not entries:
            notes.append(f"App Store page {page} returned no review entries; continuing pagination.")
            time.sleep(0.3)
            continue

        page_records: list[dict[str, Any]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            if "im:rating" not in entry:
                continue
            review_id = ((entry.get("id") or {}).get("label") or "").strip()
            if review_id and review_id in seen_ids:
                continue
            if review_id:
                seen_ids.add(review_id)

            updated_iso = ((entry.get("updated") or {}).get("label") or "").strip()
            try:
                review_dt = datetime.fromisoformat(updated_iso.replace("Z", "+00:00"))
            except ValueError:
                review_dt = None

            review_date = review_dt.date() if review_dt is not None else None

            page_records.append(
                {
                    "review_id": review_id,
                    "title": ((entry.get("title") or {}).get("label") or "").strip(),
                    "review": ((entry.get("content") or {}).get("label") or "").strip(),
                    "rating": ((entry.get("im:rating") or {}).get("label") or "").strip(),
                    "date": (review_date.isoformat() if review_date else updated_iso[:10]),
                    "language": "",
                    "_review_date_object": review_date,
                }
            )

        all_records.extend(page_records)

        oldest_on_page = min(
            (r["_review_date_object"] for r in page_records if r["_review_date_object"]),
            default=None,
        )
        if oldest_on_page and oldest_on_page < cutoff_date:
            stop_due_to_window = True
            break

        time.sleep(0.3)

    if not stop_due_to_window and len(all_records) >= page_limit * 50:
        notes.append(
            "Reached App Store RSS pagination limit; older reviews beyond this point are not "
            "retrievable through the public feed."
        )

    in_window: list[dict[str, Any]] = []
    for record in all_records:
        review_date = record.get("_review_date_object")
        if review_date is None:
            continue
        if review_date >= cutoff_date:
            clean_record = {k: v for k, v in record.items() if not k.startswith("_")}
            in_window.append(clean_record)

    earliest_in_window, latest_in_window = summarize_review_dates(in_window, "date")
    if in_window and earliest_in_window and earliest_in_window > cutoff_date:
        notes.append(
            "App Store public coverage did not reach the full requested lookback window. "
            "The stored snapshot contains the newest publicly reachable reviews only."
        )

    return all_records, in_window, notes


def fetch_play_store_reviews(
    *,
    package_name: str,
    country: str,
    language: str,
    cutoff_date: date,
    batch_size: int = PLAY_STORE_BATCH_SIZE,
    max_batches: int = PLAY_STORE_MAX_BATCHES,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    try:
        from google_play_scraper import Sort, reviews
    except ImportError as exc:
        raise FetchError(
            "google-play-scraper is required for Play Store ingestion. "
            "Install it with: pip install google-play-scraper"
        ) from exc

    notes: list[str] = []
    all_records: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    continuation_token = None
    stop_due_to_window = False

    for batch_index in range(max_batches):
        try:
            batch, continuation_token = reviews(
                package_name,
                lang=language,
                country=country,
                sort=Sort.NEWEST,
                count=batch_size,
                continuation_token=continuation_token,
            )
        except Exception as exc:  # noqa: BLE001 - scraper raises a broad set of network errors
            notes.append(f"Play Store batch {batch_index + 1} failed: {exc}. Stopping pagination.")
            break

        if not batch:
            break

        oldest_on_batch: date | None = None
        for item in batch:
            review_id = (item.get("reviewId") or "").strip()
            if review_id and review_id in seen_ids:
                continue
            if review_id:
                seen_ids.add(review_id)

            at_value = item.get("at")
            review_date: date | None = None
            if isinstance(at_value, datetime):
                review_date = at_value.date()
                at_serialized = at_value.isoformat()
            elif isinstance(at_value, str):
                try:
                    parsed = datetime.fromisoformat(at_value)
                    review_date = parsed.date()
                    at_serialized = at_value
                except ValueError:
                    at_serialized = at_value
            else:
                at_serialized = ""

            record = {
                "reviewId": review_id,
                "title": "",
                "content": (item.get("content") or "").strip(),
                "score": item.get("score"),
                "at": at_serialized,
                "language": language,
                "_review_date_object": review_date,
            }
            all_records.append(record)

            if review_date and (oldest_on_batch is None or review_date < oldest_on_batch):
                oldest_on_batch = review_date

        if oldest_on_batch and oldest_on_batch < cutoff_date:
            stop_due_to_window = True
            break

        if not continuation_token:
            break

        time.sleep(0.3)

    if not stop_due_to_window and len(all_records) >= max_batches * batch_size:
        notes.append(
            "Reached Play Store fetch batch limit; older reviews beyond this point were not "
            "requested in this run."
        )

    in_window: list[dict[str, Any]] = []
    for record in all_records:
        review_date = record.get("_review_date_object")
        if review_date is None:
            continue
        if review_date >= cutoff_date:
            clean_record = {k: v for k, v in record.items() if not k.startswith("_")}
            in_window.append(clean_record)

    return all_records, in_window, notes


def summarize_review_dates(rows: list[dict[str, Any]], date_key: str) -> tuple[date | None, date | None]:
    parsed_dates: list[date] = []
    for row in rows:
        raw_value = row.get(date_key)
        if not raw_value:
            continue
        if isinstance(raw_value, date) and not isinstance(raw_value, datetime):
            parsed_dates.append(raw_value)
            continue
        if isinstance(raw_value, datetime):
            parsed_dates.append(raw_value.date())
            continue
        if isinstance(raw_value, str):
            value = raw_value.strip()
            if not value:
                continue
            try:
                parsed_dates.append(date.fromisoformat(value))
                continue
            except ValueError:
                pass
            try:
                parsed_dates.append(datetime.fromisoformat(value.replace("Z", "+00:00")).date())
            except ValueError:
                continue
    if not parsed_dates:
        return None, None
    return min(parsed_dates), max(parsed_dates)


def write_csv(path: Path, fieldnames: list[str], rows: Iterable[dict[str, Any]]) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    written = 0
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})
            written += 1
    return written


def fetch_groww_reviews(
    *,
    data_dir: Path,
    lookback_weeks: int = DEFAULT_LOOKBACK_WEEKS,
    country: str = DEFAULT_COUNTRY,
    language: str = DEFAULT_LANGUAGE,
    app_store_id: str = GROWW_APP_STORE_ID,
    play_store_package: str = GROWW_PLAY_STORE_PACKAGE,
    run_date: date | None = None,
    skip_app_store: bool = False,
    skip_play_store: bool = False,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    effective_run_date = run_date or started_at.date()
    cutoff_date = effective_run_date - timedelta(weeks=lookback_weeks)
    raw_run_dir = data_dir / "raw" / effective_run_date.isoformat()

    fetch_metadata: dict[str, Any] = {
        "fetched_at": started_at.isoformat(),
        "run_date": effective_run_date.isoformat(),
        "lookback_weeks": lookback_weeks,
        "cutoff_date": cutoff_date.isoformat(),
        "sources": {},
        "notes": [
            "Fetched from public store-accessible review sources.",
            "Stored source files omit reviewer usernames and keep only the fields needed for Phase 1 ingestion.",
            "Raw review text is stored exactly as fetched; Phase 1 sanitization happens during ingestion before normalized outputs are written.",
        ],
    }

    raw_run_dir.mkdir(parents=True, exist_ok=True)
    app_store_csv = raw_run_dir / "groww_app_store_reviews.csv"
    play_store_csv = raw_run_dir / "groww_play_store_reviews.csv"

    if not skip_app_store:
        _app_total, app_in_window, app_notes = fetch_app_store_reviews(
            app_id=app_store_id,
            country=country,
            cutoff_date=cutoff_date,
        )
        app_earliest, app_latest = summarize_review_dates(app_in_window, "date")
        app_written = write_csv(
            app_store_csv,
            ["review_id", "title", "review", "rating", "date", "language"],
            app_in_window,
        )
        fetch_metadata["sources"]["app_store"] = {
            "app_id": app_store_id,
            "source": "app_store",
            "csv_path": str(app_store_csv),
            "fetched_reviews": app_written,
            "earliest_review_date": app_earliest.isoformat() if app_earliest else None,
            "latest_review_date": app_latest.isoformat() if app_latest else None,
            "warnings": app_notes,
        }
    else:
        fetch_metadata["sources"]["app_store"] = {"skipped": True}

    if not skip_play_store:
        try:
            _play_total, play_in_window, play_notes = fetch_play_store_reviews(
                package_name=play_store_package,
                country=country,
                language=language,
                cutoff_date=cutoff_date,
            )
        except FetchError as exc:
            fetch_metadata["sources"]["play_store"] = {
                "package_name": play_store_package,
                "source": "play_store",
                "csv_path": None,
                "fetched_reviews": 0,
                "earliest_review_date": None,
                "latest_review_date": None,
                "warnings": [str(exc)],
                "error": True,
            }
        else:
            play_earliest, play_latest = summarize_review_dates(play_in_window, "at")
            play_written = write_csv(
                play_store_csv,
                ["reviewId", "title", "content", "score", "at", "language"],
                play_in_window,
            )
            fetch_metadata["sources"]["play_store"] = {
                "package_name": play_store_package,
                "source": "play_store",
                "csv_path": str(play_store_csv),
                "fetched_reviews": play_written,
                "earliest_review_date": play_earliest.isoformat() if play_earliest else None,
                "latest_review_date": play_latest.isoformat() if play_latest else None,
                "warnings": play_notes,
            }
    else:
        fetch_metadata["sources"]["play_store"] = {"skipped": True}

    fetch_metadata["finished_at"] = datetime.now(timezone.utc).isoformat()
    fetch_metadata["raw_output_directory"] = str(raw_run_dir)

    try:
        from .store_ratings import fetch_groww_store_ratings

        listing_ratings = fetch_groww_store_ratings(country=country, language=language)
        fetch_metadata["store_listing_ratings"] = listing_ratings
        ratings_path = data_dir / "store_ratings.json"
        ratings_path.parent.mkdir(parents=True, exist_ok=True)
        ratings_path.write_text(json.dumps(listing_ratings, indent=2), encoding="utf-8")
        fetch_metadata["store_ratings_path"] = str(ratings_path)
    except FetchError as exc:
        fetch_metadata["notes"].append(f"Store listing ratings unavailable: {exc}")

    metadata_path = raw_run_dir / "fetch_manifest.json"
    metadata_path.write_text(json.dumps(fetch_metadata, indent=2), encoding="utf-8")
    fetch_metadata["metadata_path"] = str(metadata_path)
    return fetch_metadata


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Fetch the last N weeks of Groww App Store and Play Store reviews and "
            "store them as CSV exports for Phase 1 ingestion."
        )
    )
    parser.add_argument(
        "--data-dir",
        type=Path,
        default=Path("data"),
        help="Directory where the fetched CSV exports and metadata are saved.",
    )
    parser.add_argument(
        "--lookback-weeks",
        type=int,
        default=DEFAULT_LOOKBACK_WEEKS,
        help="How many weeks of reviews to fetch from each source.",
    )
    parser.add_argument(
        "--country",
        default=DEFAULT_COUNTRY,
        help="Storefront country code, defaults to 'in' for Groww's primary market.",
    )
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help="Language code for Play Store reviews.",
    )
    parser.add_argument(
        "--app-store-id",
        default=GROWW_APP_STORE_ID,
        help="Apple App Store numeric identifier for the Groww app.",
    )
    parser.add_argument(
        "--play-store-package",
        default=GROWW_PLAY_STORE_PACKAGE,
        help="Google Play Store package identifier for the Groww app.",
    )
    parser.add_argument(
        "--run-date",
        type=date.fromisoformat,
        help="Optional override for the reference run date in ISO format.",
    )
    parser.add_argument("--skip-app-store", action="store_true", help="Skip the App Store fetch.")
    parser.add_argument("--skip-play-store", action="store_true", help="Skip the Play Store fetch.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    metadata = fetch_groww_reviews(
        data_dir=args.data_dir,
        lookback_weeks=args.lookback_weeks,
        country=args.country,
        language=args.language,
        app_store_id=args.app_store_id,
        play_store_package=args.play_store_package,
        run_date=args.run_date,
        skip_app_store=args.skip_app_store,
        skip_play_store=args.skip_play_store,
    )

    print(json.dumps(metadata, indent=2))

    any_records = any(
        isinstance(source, dict) and source.get("fetched_reviews", 0) > 0
        for source in metadata["sources"].values()
    )
    return 0 if any_records else 1


if __name__ == "__main__":
    sys.exit(main())
