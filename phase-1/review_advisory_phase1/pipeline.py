from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
import uuid
from dataclasses import asdict, dataclass, field
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any


COLUMN_ALIASES: dict[str, dict[str, dict[str, list[str]]]] = {
    "app_store": {
        "required": {
            "rating": ["rating", "stars"],
            "review_text": ["review", "review_text", "body", "content"],
            "review_date": ["date", "review_date", "created_at", "updated_at"],
        },
        "optional": {
            "title": ["title", "headline"],
            "language": ["language", "locale"],
            "source_review_id": ["review_id", "id"],
        },
    },
    "play_store": {
        "required": {
            "rating": ["score", "rating", "stars"],
            "review_text": ["content", "review", "review_text", "body"],
            "review_date": ["at", "date", "review_date"],
        },
        "optional": {
            "title": ["title", "headline"],
            "language": ["language", "review_language", "locale"],
            "source_review_id": ["reviewid", "review_id", "id"],
        },
    },
}

EMAIL_PATTERN = re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE)
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)")
LONG_NUMERIC_ID_PATTERN = re.compile(r"(?<!\d)\d{8,}(?!\d)")
URL_PATTERN = re.compile(r"https?://\S+", re.IGNORECASE)
EMOJI_PATTERN = re.compile(
    "["
    "\U0001F1E6-\U0001F1FF"
    "\U0001F300-\U0001F5FF"
    "\U0001F600-\U0001F64F"
    "\U0001F680-\U0001F6FF"
    "\U0001F700-\U0001F77F"
    "\U0001F780-\U0001F7FF"
    "\U0001F800-\U0001F8FF"
    "\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF"
    "\u2600-\u26FF"
    "\u2700-\u27BF"
    "]+",
    re.UNICODE,
)
NON_LATIN_SCRIPT_PATTERN = re.compile(
    "["
    "\u0400-\u04FF"
    "\u0590-\u05FF"
    "\u0600-\u06FF"
    "\u0900-\u097F"
    "\u0980-\u09FF"
    "\u0A00-\u0A7F"
    "\u0A80-\u0AFF"
    "\u0B00-\u0B7F"
    "\u0B80-\u0BFF"
    "\u0C00-\u0C7F"
    "\u0C80-\u0CFF"
    "\u3040-\u30FF"
    "\u3400-\u4DBF"
    "\u4E00-\u9FFF"
    "\uAC00-\uD7AF"
    "]"
)
WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
COMMON_ENGLISH_TOKENS = {
    "a",
    "all",
    "amazing",
    "an",
    "and",
    "app",
    "application",
    "are",
    "awesome",
    "beginner",
    "best",
    "better",
    "brokerage",
    "but",
    "can",
    "clean",
    "easy",
    "experience",
    "fast",
    "faster",
    "for",
    "friendly",
    "from",
    "fund",
    "funds",
    "good",
    "great",
    "groww",
    "help",
    "helpful",
    "high",
    "i",
    "in",
    "interface",
    "investment",
    "investing",
    "is",
    "it",
    "latest",
    "login",
    "money",
    "mutual",
    "my",
    "nice",
    "of",
    "on",
    "payment",
    "payments",
    "platform",
    "portfolio",
    "reliable",
    "service",
    "simple",
    "smooth",
    "smoothly",
    "so",
    "stock",
    "stocks",
    "support",
    "the",
    "this",
    "to",
    "today",
    "trade",
    "trading",
    "understand",
    "update",
    "use",
    "useful",
    "very",
    "was",
    "well",
    "with",
    "works",
}
MIN_REVIEW_WORD_COUNT = 7

PII_PATTERNS: dict[str, re.Pattern[str]] = {
    "email": EMAIL_PATTERN,
    "long_numeric_id": LONG_NUMERIC_ID_PATTERN,
    "phone": PHONE_PATTERN,
    "url": URL_PATTERN,
}

DATE_FORMATS = (
    "%Y-%m-%d",
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d %H:%M",
    "%d-%m-%Y",
    "%d-%m-%Y %H:%M:%S",
    "%m-%d-%Y",
    "%b %d, %Y",
    "%B %d, %Y",
)


class SourceFormatError(ValueError):
    pass


class ValidationError(ValueError):
    pass


@dataclass(frozen=True)
class CanonicalReview:
    source: str
    rating: int
    title: str
    review_text: str
    review_date: date
    language: str
    ingested_at: datetime
    review_id_hash: str

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["review_date"] = self.review_date.isoformat()
        payload["ingested_at"] = self.ingested_at.isoformat()
        return payload


@dataclass
class SourceStats:
    total_rows: int = 0
    normalized_rows: int = 0
    dropped_missing_required: int = 0
    dropped_invalid_rating: int = 0
    dropped_invalid_date: int = 0
    dropped_outside_window: int = 0
    dropped_after_sanitization: int = 0
    dropped_non_english: int = 0
    dropped_too_short: int = 0
    duplicates_removed: int = 0
    emojis_removed: int = 0
    pii_redactions: int = 0
    optional_title_missing: int = 0
    optional_language_missing: int = 0


@dataclass
class PipelineRunResult:
    normalized_reviews: list[CanonicalReview]
    metadata: dict[str, Any]
    output_paths: dict[str, str] = field(default_factory=dict)


class ReviewIngestionPipeline:
    def execute(
        self,
        *,
        app_store_csv: str | Path | None = None,
        play_store_csv: str | Path | None = None,
        output_dir: str | Path | None = None,
        run_date: date | None = None,
        lookback_weeks: int = 8,
        min_reviews_for_confidence: int = 5,
    ) -> PipelineRunResult:
        if app_store_csv is None and play_store_csv is None:
            raise ValueError("At least one source CSV path must be provided.")

        run_started_at = datetime.now(timezone.utc)
        effective_run_date = run_date or run_started_at.date()
        window_start = effective_run_date - timedelta(weeks=lookback_weeks)
        run_id = f"phase1-{effective_run_date.isoformat()}-{uuid.uuid4().hex[:8]}"

        warnings: list[str] = []
        source_failures: list[dict[str, str]] = []
        source_stats = {
            "app_store": SourceStats(),
            "play_store": SourceStats(),
        }

        review_index: dict[str, CanonicalReview] = {}
        source_paths = {
            "app_store": Path(app_store_csv) if app_store_csv is not None else None,
            "play_store": Path(play_store_csv) if play_store_csv is not None else None,
        }

        for source_name, source_path in source_paths.items():
            if source_path is None:
                warnings.append(f"No {source_name} source file was supplied for this run.")
                continue

            try:
                reviews, stats, source_warnings = self._load_source(
                    source_name=source_name,
                    source_path=source_path,
                    window_start=window_start,
                    window_end=effective_run_date,
                    ingested_at=run_started_at,
                )
                source_stats[source_name] = stats
                warnings.extend(source_warnings)
            except (OSError, SourceFormatError) as exc:
                source_failures.append(
                    {
                        "source": source_name,
                        "path": str(source_path),
                        "error": str(exc),
                    }
                )
                warnings.append(f"{source_name} failed ingestion: {exc}")
                continue

            for review in reviews:
                if review.review_id_hash in review_index:
                    source_stats[source_name].duplicates_removed += 1
                    continue
                review_index[review.review_id_hash] = review
                source_stats[source_name].normalized_rows += 1

        normalized_reviews = sorted(
            review_index.values(),
            key=lambda review: (review.review_date, review.source, review.review_id_hash),
        )

        low_confidence = 0 < len(normalized_reviews) < min_reviews_for_confidence
        if low_confidence:
            warnings.append(
                "The normalized review set is smaller than the confidence threshold for a "
                "weekly pulse. Review downstream outputs cautiously."
            )

        status = "completed"
        if not normalized_reviews:
            status = "failed"
            warnings.append(
                "No valid reviews remained after validation, window filtering, privacy "
                "sanitization, and deduplication."
            )
        elif warnings or source_failures or low_confidence:
            status = "completed_with_warnings"

        run_finished_at = datetime.now(timezone.utc)
        totals = self._aggregate_totals(source_stats)

        metadata = {
            "run_id": run_id,
            "status": status,
            "run_started_at": run_started_at.isoformat(),
            "run_finished_at": run_finished_at.isoformat(),
            "reporting_window": {
                "start_date": window_start.isoformat(),
                "end_date": effective_run_date.isoformat(),
                "lookback_weeks": lookback_weeks,
            },
            "inputs": {
                "app_store_csv": str(source_paths["app_store"]) if source_paths["app_store"] else None,
                "play_store_csv": str(source_paths["play_store"]) if source_paths["play_store"] else None,
            },
            "assumptions": {
                "min_reviews_for_confidence": min_reviews_for_confidence,
                "accepted_sources": ["app_store", "play_store"],
                "output_scope": "Phase 1 ingestion only",
                "normalized_review_language": "en",
                "minimum_review_word_count": MIN_REVIEW_WORD_COUNT,
                "emoji_policy": "strip emojis from retained reviews",
            },
            "low_confidence": low_confidence,
            "source_failures": source_failures,
            "warnings": warnings,
            "source_stats": {
                source_name: asdict(stats) for source_name, stats in source_stats.items()
            },
            "totals": totals,
        }

        result = PipelineRunResult(normalized_reviews=normalized_reviews, metadata=metadata)
        if output_dir is not None:
            result.output_paths = self._write_outputs(
                output_dir=Path(output_dir),
                run_id=run_id,
                reviews=normalized_reviews,
                metadata=metadata,
            )
        return result

    def _load_source(
        self,
        *,
        source_name: str,
        source_path: Path,
        window_start: date,
        window_end: date,
        ingested_at: datetime,
    ) -> tuple[list[CanonicalReview], SourceStats, list[str]]:
        if not source_path.exists():
            raise SourceFormatError(f"Source file does not exist: {source_path}")
        if source_path.suffix.lower() != ".csv":
            raise SourceFormatError("Only CSV review exports are supported in Phase 1.")

        stats = SourceStats()
        warnings: list[str] = []
        normalized_reviews: list[CanonicalReview] = []

        with source_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.DictReader(handle)
            if reader.fieldnames is None:
                raise SourceFormatError(f"{source_name} export is missing a CSV header row.")
            column_map = self._resolve_column_map(source_name, reader.fieldnames)

            for row_number, row in enumerate(reader, start=2):
                stats.total_rows += 1

                raw_rating = self._read_column(row, column_map["rating"])
                raw_text = self._read_column(row, column_map["review_text"])
                raw_date = self._read_column(row, column_map["review_date"])
                raw_title = self._read_column(row, column_map.get("title"))
                raw_language = self._read_column(row, column_map.get("language"))
                raw_source_review_id = self._read_column(row, column_map.get("source_review_id"))

                if not raw_rating or not raw_text or not raw_date:
                    stats.dropped_missing_required += 1
                    continue

                try:
                    rating = self._parse_rating(raw_rating)
                except ValidationError:
                    stats.dropped_invalid_rating += 1
                    continue

                try:
                    review_date = self._parse_review_date(raw_date)
                except ValidationError:
                    stats.dropped_invalid_date += 1
                    continue

                if review_date < window_start or review_date > window_end:
                    stats.dropped_outside_window += 1
                    continue

                sanitized_title, title_redactions, title_emojis_removed = self._sanitize_text(raw_title)
                sanitized_text, text_redactions, text_emojis_removed = self._sanitize_text(raw_text)
                stats.emojis_removed += title_emojis_removed + text_emojis_removed

                if self._is_explicitly_non_english(raw_language, sanitized_title, sanitized_text):
                    stats.dropped_non_english += 1
                    continue

                if not self._is_usable_text(sanitized_text):
                    stats.dropped_after_sanitization += 1
                    continue

                if not raw_title:
                    stats.optional_title_missing += 1
                if not raw_language:
                    stats.optional_language_missing += 1

                total_redactions = len(title_redactions) + len(text_redactions)
                stats.pii_redactions += total_redactions

                if not self._is_english_review(raw_language, sanitized_title, sanitized_text):
                    stats.dropped_non_english += 1
                    continue

                if self._count_meaningful_words(sanitized_text) < MIN_REVIEW_WORD_COUNT:
                    stats.dropped_too_short += 1
                    continue

                canonical_review = CanonicalReview(
                    source=source_name,
                    rating=rating,
                    title=sanitized_title,
                    review_text=sanitized_text,
                    review_date=review_date,
                    language="en",
                    ingested_at=ingested_at,
                    review_id_hash=self._build_review_hash(
                        source_name=source_name,
                        source_review_id=raw_source_review_id,
                        rating=rating,
                        title=sanitized_title,
                        review_text=sanitized_text,
                        review_date=review_date,
                    ),
                )
                normalized_reviews.append(canonical_review)

            if stats.total_rows == 0:
                warnings.append(f"{source_name} source file contained no data rows.")

        if stats.optional_language_missing and stats.optional_language_missing == stats.total_rows:
            warnings.append(
                f"{source_name} export did not include language values; Phase 1 inferred "
                "English heuristically and dropped non-English reviews."
            )

        if stats.optional_title_missing and stats.optional_title_missing == stats.total_rows:
            warnings.append(
                f"{source_name} export did not include titles; normalization continued because "
                "titles are optional in Phase 1."
            )

        if stats.total_rows and not normalized_reviews:
            warnings.append(
                f"{source_name} provided rows but none survived validation, language filtering, "
                "word-count filtering, and window checks."
            )

        return normalized_reviews, stats, warnings

    def _resolve_column_map(
        self,
        source_name: str,
        fieldnames: list[str],
    ) -> dict[str, str | None]:
        config = COLUMN_ALIASES[source_name]
        normalized_headers = {header.strip().lower(): header for header in fieldnames}
        column_map: dict[str, str | None] = {}
        missing_required: list[str] = []

        for canonical_name, aliases in config["required"].items():
            match = self._first_header_match(normalized_headers, aliases)
            if match is None:
                missing_required.append(canonical_name)
            column_map[canonical_name] = match

        for canonical_name, aliases in config["optional"].items():
            column_map[canonical_name] = self._first_header_match(normalized_headers, aliases)

        if missing_required:
            raise SourceFormatError(
                f"{source_name} export is missing required columns: "
                + ", ".join(sorted(missing_required))
            )
        return column_map

    @staticmethod
    def _first_header_match(
        normalized_headers: dict[str, str],
        aliases: list[str],
    ) -> str | None:
        for alias in aliases:
            header = normalized_headers.get(alias.lower())
            if header is not None:
                return header
        return None

    @staticmethod
    def _read_column(row: dict[str, str | None], column_name: str | None) -> str:
        if column_name is None:
            return ""
        value = row.get(column_name, "")
        return value.strip() if isinstance(value, str) else ""

    @staticmethod
    def _parse_rating(raw_rating: str) -> int:
        try:
            rating = int(float(raw_rating))
        except ValueError as exc:
            raise ValidationError(f"Invalid rating value: {raw_rating}") from exc
        if rating < 1 or rating > 5:
            raise ValidationError(f"Rating must be between 1 and 5: {raw_rating}")
        return rating

    @staticmethod
    def _parse_review_date(raw_date: str) -> date:
        value = raw_date.strip()
        if not value:
            raise ValidationError("Review date is missing.")

        slash_match = re.fullmatch(r"(\d{1,2})/(\d{1,2})/(\d{4})", value)
        if slash_match:
            first = int(slash_match.group(1))
            second = int(slash_match.group(2))
            year = int(slash_match.group(3))
            if first <= 12 and second <= 12 and first != second:
                raise ValidationError(f"Ambiguous slash date format: {raw_date}")
            if first > 12:
                return date(year, second, first)
            return date(year, first, second)

        try:
            return date.fromisoformat(value)
        except ValueError:
            pass

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            pass

        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(value, fmt).date()
            except ValueError:
                continue

        raise ValidationError(f"Unsupported review date format: {raw_date}")

    @staticmethod
    def _sanitize_text(raw_value: str) -> tuple[str, list[str], int]:
        emoji_matches = EMOJI_PATTERN.findall(raw_value or "")
        without_emoji = EMOJI_PATTERN.sub(" ", raw_value or "")
        without_emoji = without_emoji.replace("\u200d", " ").replace("\ufe0f", " ")
        value = re.sub(r"\s+", " ", without_emoji).strip()
        redactions: list[str] = []
        if not value:
            return "", redactions, len(emoji_matches)

        sanitized = value
        for label, pattern in PII_PATTERNS.items():
            if pattern.search(sanitized):
                redactions.append(label)
                sanitized = pattern.sub(f"[REDACTED_{label.upper()}]", sanitized)
        sanitized = re.sub(r"\s+", " ", sanitized).strip()
        return sanitized, redactions, len(emoji_matches)

    @staticmethod
    def _is_usable_text(value: str) -> bool:
        if not value:
            return False
        cleaned = re.sub(r"\[REDACTED_[A-Z_]+\]", "", value)
        cleaned = re.sub(r"[^A-Za-z0-9]+", "", cleaned)
        return len(cleaned) >= 3

    @staticmethod
    def _normalize_language(raw_language: str) -> str:
        value = (raw_language or "").strip().lower().replace("_", "-")
        if not value:
            return ""
        if value.startswith("en"):
            return "en"
        return value

    @staticmethod
    def _count_meaningful_words(value: str) -> int:
        cleaned = re.sub(r"\[REDACTED_[A-Z_]+\]", " ", value)
        return len(WORD_PATTERN.findall(cleaned))

    @staticmethod
    def _is_explicitly_non_english(raw_language: str, title: str, review_text: str) -> bool:
        normalized_language = ReviewIngestionPipeline._normalize_language(raw_language)
        combined = f"{title} {review_text}".strip()
        if normalized_language and normalized_language != "en":
            return True
        return bool(combined and NON_LATIN_SCRIPT_PATTERN.search(combined))

    @staticmethod
    def _is_english_review(raw_language: str, title: str, review_text: str) -> bool:
        normalized_language = ReviewIngestionPipeline._normalize_language(raw_language)
        combined = f"{title} {review_text}".strip()
        if not combined:
            return False

        if ReviewIngestionPipeline._is_explicitly_non_english(raw_language, title, review_text):
            return False

        total_letters = sum(1 for char in combined if char.isalpha())
        latin_letters = sum(
            1
            for char in combined
            if char.isalpha() and "LATIN" in unicodedata.name(char, "")
        )
        if total_letters and latin_letters / total_letters < 0.85:
            return False

        if normalized_language == "en":
            return True

        tokens = [token.lower() for token in WORD_PATTERN.findall(combined)]
        if not tokens:
            return False

        common_hits = sum(1 for token in tokens if token in COMMON_ENGLISH_TOKENS)
        return common_hits >= 2

    @staticmethod
    def _build_review_hash(
        *,
        source_name: str,
        source_review_id: str,
        rating: int,
        title: str,
        review_text: str,
        review_date: date,
    ) -> str:
        if source_review_id:
            key = f"{source_name}|{source_review_id.strip().lower()}"
        else:
            normalized_title = title.strip().lower()
            normalized_text = review_text.strip().lower()
            key = (
                f"{source_name}|{rating}|{normalized_title}|{normalized_text}|"
                f"{review_date.isoformat()}"
            )
        return hashlib.sha256(key.encode("utf-8")).hexdigest()

    @staticmethod
    def _aggregate_totals(source_stats: dict[str, SourceStats]) -> dict[str, int]:
        totals = SourceStats()
        for stats in source_stats.values():
            totals.total_rows += stats.total_rows
            totals.normalized_rows += stats.normalized_rows
            totals.dropped_missing_required += stats.dropped_missing_required
            totals.dropped_invalid_rating += stats.dropped_invalid_rating
            totals.dropped_invalid_date += stats.dropped_invalid_date
            totals.dropped_outside_window += stats.dropped_outside_window
            totals.dropped_after_sanitization += stats.dropped_after_sanitization
            totals.dropped_non_english += stats.dropped_non_english
            totals.dropped_too_short += stats.dropped_too_short
            totals.duplicates_removed += stats.duplicates_removed
            totals.emojis_removed += stats.emojis_removed
            totals.pii_redactions += stats.pii_redactions
            totals.optional_title_missing += stats.optional_title_missing
            totals.optional_language_missing += stats.optional_language_missing
        return asdict(totals)

    @staticmethod
    def _write_outputs(
        *,
        output_dir: Path,
        run_id: str,
        reviews: list[CanonicalReview],
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        run_dir = output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        normalized_reviews_path = run_dir / "normalized_reviews.json"
        run_metadata_path = run_dir / "run_metadata.json"

        normalized_reviews_path.write_text(
            json.dumps([review.to_dict() for review in reviews], indent=2),
            encoding="utf-8",
        )
        run_metadata_path.write_text(
            json.dumps(metadata, indent=2),
            encoding="utf-8",
        )

        return {
            "run_directory": str(run_dir),
            "normalized_reviews": str(normalized_reviews_path),
            "run_metadata": str(run_metadata_path),
        }


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 1 review ingestion pipeline for the Review Advisory Agent."
    )
    parser.add_argument("--app-store-csv", type=Path, help="Path to the App Store CSV export.")
    parser.add_argument("--play-store-csv", type=Path, help="Path to the Play Store CSV export.")
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where normalized outputs and run metadata are written.",
    )
    parser.add_argument(
        "--run-date",
        type=date.fromisoformat,
        help="ISO date used as the run date, e.g. 2026-05-11.",
    )
    parser.add_argument(
        "--lookback-weeks",
        type=int,
        default=None,
        help="Weeks of reviews to read from CSVs (default: 1 if --incremental, else 8).",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Ingest only the latest fetch window, merge into data/warehouse, and expose the rolling corpus to Phase 2.",
    )
    parser.add_argument(
        "--bootstrap-warehouse",
        action="store_true",
        help="Replace the warehouse from this run (use with a full 8-week ingest to seed history).",
    )
    parser.add_argument(
        "--warehouse-dir",
        type=Path,
        default=Path("data/warehouse"),
        help="Directory for the rolling normalized review warehouse.",
    )
    parser.add_argument(
        "--rolling-window-weeks",
        type=int,
        default=8,
        help="Keep this many weeks of reviews in the warehouse when using --incremental.",
    )
    parser.add_argument(
        "--min-reviews-for-confidence",
        type=int,
        default=5,
        help="Minimum number of valid reviews before the run avoids a low-confidence warning.",
    )
    return parser


def main() -> int:
    parser = build_argument_parser()
    args = parser.parse_args()

    if args.lookback_weeks is None:
        lookback_weeks = 1 if args.incremental else 8
    else:
        lookback_weeks = args.lookback_weeks

    pipeline = ReviewIngestionPipeline()
    result = pipeline.execute(
        app_store_csv=args.app_store_csv,
        play_store_csv=args.play_store_csv,
        output_dir=args.output_dir,
        run_date=args.run_date,
        lookback_weeks=lookback_weeks,
        min_reviews_for_confidence=args.min_reviews_for_confidence,
    )

    if result.metadata["status"] != "failed":
        effective_run_date = args.run_date
        if effective_run_date is None:
            effective_run_date = date.fromisoformat(
                result.metadata["reporting_window"]["end_date"]
            )
        if args.bootstrap_warehouse:
            from .warehouse import bootstrap_warehouse_from_run

            result = bootstrap_warehouse_from_run(
                run_result=result,
                run_date=effective_run_date,
                warehouse_dir=args.warehouse_dir,
                rolling_window_weeks=args.rolling_window_weeks,
            )
        elif args.incremental:
            from .warehouse import merge_incremental_run

            result = merge_incremental_run(
                run_result=result,
                run_date=effective_run_date,
                warehouse_dir=args.warehouse_dir,
                rolling_window_weeks=args.rolling_window_weeks,
            )

    print(json.dumps({"metadata": result.metadata, "output_paths": result.output_paths}, indent=2))
    return 0 if result.metadata["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
