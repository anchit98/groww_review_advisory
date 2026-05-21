from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

from .models import (
    CandidateTheme,
    ConsolidationCandidateTheme,
    ConsolidationRequest,
    ConsolidationResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    FinalNoteRequest,
    FinalTheme,
    MAX_TOP_THEMES,
    QuoteCandidate,
    ReviewEvidence,
    SourceMix,
    WeeklyPulseResponse,
)


WORD_PATTERN = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
NON_ALNUM_PATTERN = re.compile(r"[^a-z0-9]+")
JSON_FENCE_PATTERN = re.compile(r"^```(?:json)?\s*|\s*```$", re.IGNORECASE)
MAX_WORKING_REVIEWS = 1000
MAX_DISCOVERY_CALLS = 8
MAX_REVIEWS_PER_BATCH = 40
MAX_WORDS_PER_BATCH = 1800
MAX_KEYWORDS_PER_REVIEW = 5
MAX_QUOTE_CANDIDATES_PER_THEME = 5
MAX_LLM_REVIEW_CHARS = 220
MAX_DISCOVERY_RESPONSE_TOKENS = 1200
MAX_CONSOLIDATION_RESPONSE_TOKENS = 1500
MAX_FINAL_NOTE_RESPONSE_TOKENS = 1200
DEFAULT_GROQ_MODEL = "llama-3.3-70b-versatile"
DEFAULT_GROQ_TIMEOUT_S = 60.0
DEFAULT_GROQ_TEMPERATURE = 0.1
SOFT_REQUESTS_PER_MINUTE = 4
SOFT_TOKENS_PER_MINUTE = 10_000
# Complaint / negative evidence: 1★ and 2★ (not 1★ only).
NEGATIVE_RATING_MAX = 2
POSITIVE_RATING_MIN = 4

WORKING_SET_WEIGHTS = {"1-2": 0.55, "3": 0.15, "4-5": 0.30}
DISCOVERY_SLICE_TARGETS: dict[tuple[str, str], int] = {
    ("app_store", "1-2"): 15,
    ("play_store", "1-2"): 70,
    ("mixed", "3"): 20,
    ("app_store", "4-5"): 10,
    ("play_store", "4-5"): 30,
}

STOPWORDS = {
    "a",
    "about",
    "after",
    "again",
    "all",
    "also",
    "am",
    "an",
    "and",
    "any",
    "app",
    "are",
    "as",
    "at",
    "be",
    "because",
    "been",
    "before",
    "being",
    "between",
    "both",
    "but",
    "by",
    "can",
    "could",
    "did",
    "do",
    "does",
    "doing",
    "done",
    "down",
    "during",
    "each",
    "even",
    "every",
    "for",
    "from",
    "get",
    "got",
    "groww",
    "had",
    "has",
    "have",
    "having",
    "how",
    "i",
    "if",
    "in",
    "into",
    "is",
    "it",
    "its",
    "just",
    "like",
    "make",
    "many",
    "more",
    "most",
    "much",
    "my",
    "need",
    "now",
    "of",
    "on",
    "one",
    "only",
    "or",
    "other",
    "our",
    "out",
    "really",
    "same",
    "should",
    "so",
    "some",
    "still",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "time",
    "to",
    "too",
    "up",
    "use",
    "used",
    "using",
    "very",
    "was",
    "we",
    "well",
    "were",
    "what",
    "when",
    "which",
    "while",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
}


class Phase2Error(RuntimeError):
    pass


@dataclass(frozen=True)
class GroqConfig:
    api_key: str
    model: str = DEFAULT_GROQ_MODEL
    base_url: str = "https://api.groq.com/openai/v1/chat/completions"
    timeout_s: float = DEFAULT_GROQ_TIMEOUT_S
    temperature: float = DEFAULT_GROQ_TEMPERATURE


@dataclass
class Phase2ExecutionResult:
    metadata: dict[str, Any]
    output_paths: dict[str, str]


class GroqClient:
    def __init__(self, config: GroqConfig) -> None:
        self.config = config

    def complete_json(self, *, system_prompt: str, user_prompt: str) -> dict[str, Any]:
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }

        request = urllib.request.Request(
            self.config.base_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.config.api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "ReviewAdvisoryAgent/1.0 (+https://cursor.sh)",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=self.config.timeout_s) as response:
                response_payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8", errors="replace")
            raise Phase2Error(f"Groq API returned HTTP {exc.code}: {body}") from exc
        except urllib.error.URLError as exc:
            raise Phase2Error(f"Groq API request failed: {exc}") from exc

        try:
            content = response_payload["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise Phase2Error("Groq response did not contain a chat completion message.") from exc
        return extract_json_object(content)


class GroqRateLimiter:
    def __init__(
        self,
        *,
        requests_per_minute: int = SOFT_REQUESTS_PER_MINUTE,
        tokens_per_minute: int = SOFT_TOKENS_PER_MINUTE,
    ) -> None:
        self.requests_per_minute = requests_per_minute
        self.tokens_per_minute = tokens_per_minute
        self._history: list[tuple[float, int]] = []

    def wait_for_budget(self, estimated_tokens: int) -> None:
        while True:
            now = time.monotonic()
            self._history = [
                (timestamp, tokens)
                for timestamp, tokens in self._history
                if now - timestamp < 60.0
            ]
            requests_used = len(self._history)
            tokens_used = sum(tokens for _timestamp, tokens in self._history)
            if (
                requests_used < self.requests_per_minute
                and tokens_used + estimated_tokens <= self.tokens_per_minute
            ):
                self._history.append((now, estimated_tokens))
                return

            if not self._history:
                time.sleep(0.25)
                continue

            oldest_timestamp = min(timestamp for timestamp, _tokens in self._history)
            sleep_for = max(0.25, 60.1 - (now - oldest_timestamp))
            time.sleep(sleep_for)


class Phase2Pipeline:
    def execute(
        self,
        *,
        normalized_reviews_path: str | Path,
        phase1_metadata_path: str | Path | None = None,
        output_dir: str | Path | None = None,
        dry_run: bool = False,
        groq_api_key: str | None = None,
        groq_model: str = DEFAULT_GROQ_MODEL,
    ) -> Phase2ExecutionResult:
        normalized_path = Path(normalized_reviews_path)
        metadata_path = self._resolve_phase1_metadata_path(normalized_path, phase1_metadata_path)
        phase1_metadata = self._load_json(metadata_path)
        raw_reviews = self._load_json(normalized_path)
        reviews = self._load_phase1_reviews(raw_reviews)

        handoff_summary = self._validate_phase1_handoff(
            reviews=reviews,
            phase1_metadata=phase1_metadata,
            normalized_reviews_path=normalized_path,
            phase1_metadata_path=metadata_path,
        )

        reporting_start = date.fromisoformat(phase1_metadata["reporting_window"]["start_date"])
        reporting_end = date.fromisoformat(phase1_metadata["reporting_window"]["end_date"])
        coverage_notes = self._load_coverage_notes(phase1_metadata, metadata_path)
        prepared_reviews = self._prepare_review_evidence(reviews)
        working_reviews = self._select_working_review_set(prepared_reviews)
        discovery_requests = self._build_discovery_requests(
            working_reviews,
            reporting_start=reporting_start,
            reporting_end=reporting_end,
        )
        discovery_prompts = [
            {
                "batch_id": request.batch_id,
                "system_prompt": self._render_discovery_system_prompt(),
                "user_prompt": self._render_discovery_user_prompt(request),
            }
            for request in discovery_requests
        ]

        run_started_at = datetime.now(timezone.utc)
        run_id = f"phase2-{reporting_end.isoformat()}-{uuid.uuid4().hex[:8]}"

        metadata: dict[str, Any] = {
            "run_id": run_id,
            "status": "prepared" if dry_run else "running",
            "run_started_at": run_started_at.isoformat(),
            "phase1_handoff": handoff_summary,
            "input_paths": {
                "normalized_reviews": str(normalized_path),
                "phase1_metadata": str(metadata_path),
            },
            "reporting_window": {
                "start_date": reporting_start.isoformat(),
                "end_date": reporting_end.isoformat(),
                "lookback_weeks": phase1_metadata["reporting_window"]["lookback_weeks"],
            },
            "source_mix": self._build_source_mix(reviews).model_dump(mode="json"),
            "review_counts": {
                "normalized_reviews": len(reviews),
                "prepared_evidence_reviews": len(prepared_reviews),
                "working_set_reviews": len(working_reviews),
                "working_set_reviews_excluded": max(0, len(prepared_reviews) - len(working_reviews)),
                "discovery_evidence_reviews": sum(len(request.reviews) for request in discovery_requests),
                "discovery_batches": len(discovery_requests),
            },
            "coverage_notes": coverage_notes,
            "llm_provider": {
                "name": "groq",
                "model": groq_model,
                "dry_run": dry_run,
            },
            "groq_limits": {
                "provider_requests_per_minute": 30,
                "provider_requests_per_day": 1000,
                "provider_tokens_per_minute": 12000,
                "provider_tokens_per_day": 100000,
                "soft_requests_per_minute": SOFT_REQUESTS_PER_MINUTE,
                "soft_tokens_per_minute": SOFT_TOKENS_PER_MINUTE,
            },
            "phase2_limits": {
                "max_working_reviews": MAX_WORKING_REVIEWS,
                "max_discovery_calls_target": MAX_DISCOVERY_CALLS,
                "max_reviews_per_batch": MAX_REVIEWS_PER_BATCH,
                "max_words_per_batch": MAX_WORDS_PER_BATCH,
            },
        }
        metadata["groq_call_budget"] = {
            "discovery_calls": len(discovery_requests),
            "consolidation_calls": 1,
            "final_note_calls": 1,
            "total_calls": len(discovery_requests) + 2,
            "estimated_total_tokens": self._estimate_total_run_tokens(discovery_prompts),
        }

        output_paths: dict[str, str] = {}
        if output_dir is not None:
            output_paths = self._write_phase2_artifacts(
                output_dir=Path(output_dir),
                run_id=run_id,
                prepared_reviews=prepared_reviews,
                working_reviews=working_reviews,
                discovery_requests=discovery_requests,
                discovery_prompts=discovery_prompts,
                metadata=metadata,
            )

        if dry_run:
            metadata["status"] = "dry_run_prepared"
            metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
            if output_paths:
                self._rewrite_metadata_file(output_paths["run_metadata"], metadata)
            return Phase2ExecutionResult(metadata=metadata, output_paths=output_paths)

        _load_local_env_files()
        groq_api_key = groq_api_key or os.getenv("GROQ_API_KEY")
        if not groq_api_key:
            raise Phase2Error(
                "GROQ_API_KEY is required for a live Phase 2 run. "
                "Set the environment variable or use --dry-run."
            )

        client = GroqClient(GroqConfig(api_key=groq_api_key, model=groq_model))
        rate_limiter = GroqRateLimiter()

        discovery_responses: list[DiscoveryResponse] = []
        for request in discovery_requests:
            system_prompt = self._render_discovery_system_prompt()
            user_prompt = self._render_discovery_user_prompt(request)
            rate_limiter.wait_for_budget(
                self._estimate_call_tokens(system_prompt, user_prompt, MAX_DISCOVERY_RESPONSE_TOKENS)
            )
            raw_response = client.complete_json(
                system_prompt=system_prompt,
                user_prompt=user_prompt,
            )
            normalized_response = _normalize_groq_structured_output(raw_response)
            response = DiscoveryResponse.model_validate(normalized_response)
            if response.batch_id != request.batch_id:
                raise Phase2Error(
                    f"Discovery response batch_id mismatch: expected {request.batch_id}, got {response.batch_id}"
                )
            discovery_responses.append(response)

        merged_candidates = self._merge_obvious_candidate_duplicates(discovery_responses)
        consolidation_request = self._build_consolidation_request(
            merged_candidates,
            reporting_start=reporting_start,
            reporting_end=reporting_end,
            source_mix=self._build_source_mix(reviews),
            total_normalized_reviews=len(reviews),
            coverage_notes=coverage_notes,
        )
        consolidation_prompt = {
            "system_prompt": self._render_consolidation_system_prompt(),
            "user_prompt": self._render_consolidation_user_prompt(consolidation_request),
        }

        rate_limiter.wait_for_budget(
            self._estimate_call_tokens(
                consolidation_prompt["system_prompt"],
                consolidation_prompt["user_prompt"],
                MAX_CONSOLIDATION_RESPONSE_TOKENS,
            )
        )
        raw_consolidation_response = client.complete_json(
            system_prompt=consolidation_prompt["system_prompt"],
            user_prompt=consolidation_prompt["user_prompt"],
        )
        consolidation_response = ConsolidationResponse.model_validate(
            _normalize_groq_structured_output(raw_consolidation_response)
        )
        priority_final_themes = self._select_priority_final_themes(
            consolidation_response.final_themes
        )

        quote_candidates = self._build_quote_candidates(
            priority_final_themes,
            review_lookup={review.review_id_hash: review for review in reviews},
        )
        final_note_request = self._build_final_note_request(
            final_themes=priority_final_themes,
            quote_candidates=quote_candidates,
            reporting_start=reporting_start,
            reporting_end=reporting_end,
            source_mix=self._build_source_mix(reviews),
            total_normalized_reviews=len(reviews),
            coverage_notes=coverage_notes,
        )
        final_note_prompt = {
            "system_prompt": self._render_final_note_system_prompt(),
            "user_prompt": self._render_final_note_user_prompt(final_note_request),
        }

        rate_limiter.wait_for_budget(
            self._estimate_call_tokens(
                final_note_prompt["system_prompt"],
                final_note_prompt["user_prompt"],
                MAX_FINAL_NOTE_RESPONSE_TOKENS,
            )
        )
        raw_weekly_pulse = client.complete_json(
            system_prompt=final_note_prompt["system_prompt"],
            user_prompt=final_note_prompt["user_prompt"],
        )
        weekly_pulse = WeeklyPulseResponse.model_validate(
            _normalize_groq_structured_output(raw_weekly_pulse)
        )
        self._validate_final_weekly_pulse(
            weekly_pulse=weekly_pulse,
            final_note_request=final_note_request,
        )

        metadata["status"] = "completed"
        metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
        metadata["review_counts"]["merged_candidate_themes"] = len(merged_candidates)
        metadata["review_counts"]["final_themes"] = len(consolidation_response.final_themes)
        metadata["review_counts"]["quote_candidates"] = len(quote_candidates)

        if output_paths:
            artifact_dir = Path(output_paths["run_directory"])
            self._write_json(
                artifact_dir / "discovery_responses.json",
                [response.model_dump(mode="json") for response in discovery_responses],
            )
            self._write_json(
                artifact_dir / "merged_candidate_themes.json",
                [theme.model_dump(mode="json") for theme in merged_candidates],
            )
            self._write_json(
                artifact_dir / "consolidation_request.json",
                consolidation_request.model_dump(mode="json"),
            )
            self._write_json(
                artifact_dir / "consolidation_prompt.json",
                consolidation_prompt,
            )
            self._write_json(
                artifact_dir / "consolidation_response.json",
                consolidation_response.model_dump(mode="json"),
            )
            self._write_json(
                artifact_dir / "quote_candidates.json",
                [candidate.model_dump(mode="json") for candidate in quote_candidates],
            )
            self._write_json(
                artifact_dir / "final_note_request.json",
                final_note_request.model_dump(mode="json"),
            )
            self._write_json(
                artifact_dir / "final_note_prompt.json",
                final_note_prompt,
            )
            self._write_json(
                artifact_dir / "weekly_pulse.json",
                weekly_pulse.model_dump(mode="json"),
            )
            self._rewrite_metadata_file(output_paths["run_metadata"], metadata)

        return Phase2ExecutionResult(metadata=metadata, output_paths=output_paths)

    @staticmethod
    def _resolve_phase1_metadata_path(
        normalized_reviews_path: Path,
        phase1_metadata_path: str | Path | None,
    ) -> Path:
        if phase1_metadata_path is not None:
            return Path(phase1_metadata_path)
        sibling_metadata = normalized_reviews_path.with_name("run_metadata.json")
        if sibling_metadata.exists():
            return sibling_metadata
        raise Phase2Error(
            "Could not infer the Phase 1 run metadata path. Provide --phase1-metadata explicitly."
        )

    @staticmethod
    def _load_json(path: Path) -> Any:
        if not path.exists():
            raise Phase2Error(f"Required JSON file does not exist: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Phase2Error(f"Could not parse JSON file: {path}") from exc

    @staticmethod
    def _load_phase1_reviews(raw_reviews: Any) -> list[ReviewEvidence]:
        if not isinstance(raw_reviews, list):
            raise Phase2Error("Phase 1 normalized review file must contain a JSON array.")
        reviews: list[ReviewEvidence] = []
        for raw in raw_reviews:
            review = ReviewEvidence.model_validate(
                {
                    "review_id_hash": raw["review_id_hash"],
                    "source": raw["source"],
                    "rating": raw["rating"],
                    "review_date": raw["review_date"],
                    "title": raw.get("title", ""),
                    "review_text": raw["review_text"],
                }
            )
            reviews.append(review)
        return reviews

    def _validate_phase1_handoff(
        self,
        *,
        reviews: list[ReviewEvidence],
        phase1_metadata: dict[str, Any],
        normalized_reviews_path: Path,
        phase1_metadata_path: Path,
    ) -> dict[str, Any]:
        if phase1_metadata.get("status") not in ("completed", "completed_with_warnings"):
            raise Phase2Error(
                f"Phase 1 handoff is not complete. Metadata status was: {phase1_metadata.get('status')}"
            )

        assumptions = phase1_metadata.get("assumptions", {})
        if assumptions.get("normalized_review_language") != "en":
            raise Phase2Error("Phase 1 handoff must provide an English-only normalized dataset.")
        if assumptions.get("minimum_review_word_count") != 7:
            raise Phase2Error("Phase 1 handoff must enforce the 7-word minimum review rule.")
        if assumptions.get("emoji_policy") != "strip emojis from retained reviews":
            raise Phase2Error("Phase 1 handoff must provide emoji-stripped normalized reviews.")
        if phase1_metadata.get("reporting_window", {}).get("lookback_weeks") != 8:
            raise Phase2Error("Phase 1 handoff must use the 8-week reporting window.")

        if not reviews:
            raise Phase2Error("Phase 1 handoff contains no normalized reviews.")

        bad_language_reviews = [review.review_id_hash for review in reviews if review.source not in {"app_store", "play_store"}]
        if bad_language_reviews:
            raise Phase2Error("Phase 1 handoff contains invalid source identifiers.")

        return {
            "normalized_reviews_path": str(normalized_reviews_path),
            "phase1_metadata_path": str(phase1_metadata_path),
            "phase1_run_id": phase1_metadata.get("run_id"),
            "phase1_status": phase1_metadata.get("status"),
            "lookback_weeks": phase1_metadata.get("reporting_window", {}).get("lookback_weeks"),
            "minimum_review_word_count": assumptions.get("minimum_review_word_count"),
            "normalized_review_language": assumptions.get("normalized_review_language"),
            "emoji_policy": assumptions.get("emoji_policy"),
        }

    def _prepare_review_evidence(self, reviews: list[ReviewEvidence]) -> list[ReviewEvidence]:
        fingerprint_counts = Counter(self._fingerprint_text(review.review_text) for review in reviews)
        prepared: list[ReviewEvidence] = []

        for review in reviews:
            fingerprint = self._fingerprint_text(review.review_text)
            duplicate_group_id = None
            if fingerprint_counts[fingerprint] > 1:
                duplicate_group_id = hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:16]
            word_count = len(WORD_PATTERN.findall(review.review_text))
            candidate_keywords = self._extract_candidate_keywords(review.review_text)
            prepared.append(
                review.model_copy(
                    update={
                        "review_text": self._build_llm_review_text(review.review_text),
                        "word_count": word_count,
                        "candidate_keywords": candidate_keywords,
                        "duplicate_group_id": duplicate_group_id,
                    }
                )
            )

        prepared.sort(key=lambda review: (review.review_date, review.source, review.review_id_hash))
        return prepared

    def _select_working_review_set(self, reviews: list[ReviewEvidence]) -> list[ReviewEvidence]:
        if len(reviews) <= MAX_WORKING_REVIEWS:
            return list(reviews)

        app_reviews = [review for review in reviews if review.source == "app_store"]
        play_reviews = [review for review in reviews if review.source == "play_store"]

        selected = self._take_ranked_reviews(app_reviews, min(len(app_reviews), MAX_WORKING_REVIEWS))
        remaining_budget = MAX_WORKING_REVIEWS - len(selected)
        if remaining_budget <= 0:
            return selected[:MAX_WORKING_REVIEWS]

        play_slices = self._group_reviews_by_rating_band(play_reviews)
        allocated: dict[str, list[ReviewEvidence]] = {"1-2": [], "3": [], "4-5": []}
        remaining_by_band: dict[str, list[ReviewEvidence]] = {}
        remaining_quota = remaining_budget

        for rating_band in ("1-2", "3", "4-5"):
            ranked_slice = self._take_ranked_reviews(play_slices[rating_band], len(play_slices[rating_band]))
            quota = min(len(ranked_slice), int(round(remaining_budget * WORKING_SET_WEIGHTS[rating_band])))
            if rating_band == "4-5":
                quota = min(len(ranked_slice), remaining_quota)
            allocated[rating_band] = ranked_slice[:quota]
            remaining_by_band[rating_band] = ranked_slice[quota:]
            remaining_quota -= quota

        if remaining_quota > 0:
            for rating_band in ("1-2", "3", "4-5"):
                if remaining_quota <= 0:
                    break
                extra = remaining_by_band[rating_band][:remaining_quota]
                allocated[rating_band].extend(extra)
                remaining_quota -= len(extra)

        selected.extend(allocated["1-2"])
        selected.extend(allocated["3"])
        selected.extend(allocated["4-5"])
        selected = selected[:MAX_WORKING_REVIEWS]
        selected.sort(key=lambda review: (review.review_date, review.source, review.review_id_hash))
        return selected

    @staticmethod
    def _fingerprint_text(text: str) -> str:
        normalized = NON_ALNUM_PATTERN.sub(" ", text.lower()).strip()
        return re.sub(r"\s+", " ", normalized)

    @staticmethod
    def _extract_candidate_keywords(text: str, limit: int = MAX_KEYWORDS_PER_REVIEW) -> list[str]:
        tokens = [
            token.lower()
            for token in WORD_PATTERN.findall(text)
            if len(token) > 2 and token.lower() not in STOPWORDS
        ]
        if not tokens:
            return []
        counts = Counter(tokens)
        return [token for token, _count in counts.most_common(limit)]

    @staticmethod
    def _build_llm_review_text(text: str, max_length: int = MAX_LLM_REVIEW_CHARS) -> str:
        normalized = re.sub(r"\s+", " ", text).strip()
        if len(normalized) <= max_length:
            return normalized
        sentences = re.split(r"(?<=[.!?])\s+", normalized)
        snippet = sentences[0].strip() if sentences else normalized[:max_length]
        if len(snippet) < 100 and len(sentences) > 1:
            snippet = f"{snippet} {sentences[1].strip()}".strip()
        if len(snippet) <= max_length:
            return snippet
        return snippet[: max_length - 3].rstrip() + "..."

    @staticmethod
    def _take_ranked_reviews(reviews: list[ReviewEvidence], limit: int) -> list[ReviewEvidence]:
        if limit <= 0 or not reviews:
            return []
        ranked = sorted(
            reviews,
            key=lambda review: (
                review.review_date,
                min(review.word_count or 0, 80),
                len(review.candidate_keywords),
                review.review_id_hash,
            ),
            reverse=True,
        )

        selected: list[ReviewEvidence] = []
        seen_groups: set[str] = set()
        grouped_backlog: list[ReviewEvidence] = []
        for review in ranked:
            group_key = review.duplicate_group_id or review.review_id_hash
            if group_key in seen_groups:
                grouped_backlog.append(review)
                continue
            selected.append(review)
            seen_groups.add(group_key)
            if len(selected) >= limit:
                return selected

        for review in grouped_backlog:
            selected.append(review)
            if len(selected) >= limit:
                break
        return selected

    @staticmethod
    def _group_reviews_by_rating_band(reviews: list[ReviewEvidence]) -> dict[str, list[ReviewEvidence]]:
        grouped: dict[str, list[ReviewEvidence]] = {"1-2": [], "3": [], "4-5": []}
        for review in reviews:
            if review.rating <= NEGATIVE_RATING_MAX:
                grouped["1-2"].append(review)
            elif review.rating == 3:
                grouped["3"].append(review)
            else:
                grouped["4-5"].append(review)
        return grouped

    def _build_discovery_requests(
        self,
        reviews: list[ReviewEvidence],
        *,
        reporting_start: date,
        reporting_end: date,
    ) -> list[DiscoveryRequest]:
        slices: dict[tuple[str, str], list[ReviewEvidence]] = {
            ("app_store", "1-2"): [],
            ("play_store", "1-2"): [],
            ("mixed", "3"): [],
            ("app_store", "4-5"): [],
            ("play_store", "4-5"): [],
        }

        for review in reviews:
            if review.rating <= NEGATIVE_RATING_MAX:
                slices[(review.source, "1-2")].append(review)
            elif review.rating == 3:
                slices[("mixed", "3")].append(review)
            else:
                slices[(review.source, "4-5")].append(review)

        selected_slices: dict[tuple[str, str], list[ReviewEvidence]] = {}
        for slice_key, slice_reviews in slices.items():
            target = DISCOVERY_SLICE_TARGETS[slice_key]
            selected_slices[slice_key] = self._take_ranked_reviews(slice_reviews, target)

        requests: list[DiscoveryRequest] = []
        for (source_scope, rating_band), slice_reviews in selected_slices.items():
            if not slice_reviews:
                continue
            sorted_reviews = sorted(
                slice_reviews,
                key=lambda review: (review.review_date, review.review_id_hash),
            )
            for batch_index, review_batch in enumerate(self._chunk_reviews(sorted_reviews), start=1):
                batch_source_scope = (
                    ["app_store", "play_store"]
                    if source_scope == "mixed"
                    else [source_scope]
                )
                batch_id = f"{source_scope}-{rating_band}-batch-{batch_index:03d}"
                requests.append(
                    DiscoveryRequest(
                        batch_id=batch_id,
                        batch_type=self._batch_type_for_rating_band(rating_band),
                        source_scope=batch_source_scope,
                        rating_band=rating_band,  # type: ignore[arg-type]
                        reporting_start_date=reporting_start,
                        reporting_end_date=reporting_end,
                        reviews=[
                            review.model_copy(update={"slice_id": f"{source_scope}-{rating_band}"})
                            for review in review_batch
                        ],
                    )
                )
        if len(requests) > MAX_DISCOVERY_CALLS:
            raise Phase2Error(
                f"Discovery batching exceeded the configured call target of {MAX_DISCOVERY_CALLS}."
            )
        return requests

    @staticmethod
    def _batch_type_for_rating_band(rating_band: str) -> str:
        if rating_band == "1-2":
            return "complaint_slice"
        if rating_band == "4-5":
            return "praise_slice"
        return "neutral_slice"

    @staticmethod
    def _chunk_reviews(reviews: list[ReviewEvidence]) -> Iterable[list[ReviewEvidence]]:
        current_batch: list[ReviewEvidence] = []
        current_words = 0
        for review in reviews:
            snippet_words = len(WORD_PATTERN.findall(review.review_text))
            review_words = min(review.word_count or snippet_words, snippet_words)
            if current_batch and (
                len(current_batch) >= MAX_REVIEWS_PER_BATCH
                or current_words + review_words > MAX_WORDS_PER_BATCH
            ):
                yield current_batch
                current_batch = []
                current_words = 0
            current_batch.append(review)
            current_words += review_words
        if current_batch:
            yield current_batch

    @staticmethod
    def _build_source_mix(reviews: list[ReviewEvidence]) -> SourceMix:
        counts = Counter(review.source for review in reviews)
        return SourceMix(
            app_store=counts.get("app_store", 0),
            play_store=counts.get("play_store", 0),
        )

    def _merge_obvious_candidate_duplicates(
        self,
        discovery_responses: list[DiscoveryResponse],
    ) -> list[ConsolidationCandidateTheme]:
        merged: dict[tuple[str, str], ConsolidationCandidateTheme] = {}
        for response in discovery_responses:
            for candidate in response.candidate_themes:
                dedupe_key = (
                    NON_ALNUM_PATTERN.sub(" ", candidate.theme_name.lower()).strip(),
                    candidate.sentiment,
                )
                if dedupe_key not in merged:
                    merged[dedupe_key] = ConsolidationCandidateTheme(
                        candidate_theme_id=candidate.candidate_theme_id,
                        source_batch_id=response.batch_id,
                        theme_name=candidate.theme_name,
                        sentiment=candidate.sentiment,
                        summary=candidate.summary,
                        evidence_review_ids=list(candidate.evidence_review_ids),
                        recurrence_reason=candidate.recurrence_reason,
                        source_scope=list(candidate.source_scope),
                        rating_band=candidate.rating_band,
                        candidate_weight=max(1, len(candidate.evidence_review_ids)),
                    )
                    continue

                existing = merged[dedupe_key]
                merged[dedupe_key] = existing.model_copy(
                    update={
                        "evidence_review_ids": sorted(
                            set(existing.evidence_review_ids) | set(candidate.evidence_review_ids)
                        ),
                        "source_scope": sorted(
                            set(existing.source_scope) | set(candidate.source_scope)
                        ),
                        "candidate_weight": (existing.candidate_weight or 0) + max(
                            1, len(candidate.evidence_review_ids)
                        ),
                    }
                )

        return list(merged.values())

    def _build_consolidation_request(
        self,
        candidate_themes: list[ConsolidationCandidateTheme],
        *,
        reporting_start: date,
        reporting_end: date,
        source_mix: SourceMix,
        total_normalized_reviews: int,
        coverage_notes: list[str],
    ) -> ConsolidationRequest:
        return ConsolidationRequest(
            reporting_start_date=reporting_start,
            reporting_end_date=reporting_end,
            total_normalized_reviews=total_normalized_reviews,
            source_mix=source_mix,
            coverage_notes=coverage_notes,
            candidate_themes=candidate_themes,
        )

    def _build_quote_candidates(
        self,
        final_themes: list[FinalTheme],
        *,
        review_lookup: dict[str, ReviewEvidence],
    ) -> list[QuoteCandidate]:
        candidates: list[QuoteCandidate] = []
        for final_theme in final_themes:
            theme_reviews = [
                review_lookup[review_id]
                for review_id in final_theme.supporting_review_ids
                if review_id in review_lookup
            ]
            selected_reviews = self._select_quote_reviews_for_theme(theme_reviews, final_theme)
            for index, review in enumerate(selected_reviews, start=1):
                candidates.append(
                    QuoteCandidate(
                        quote_candidate_id=f"{final_theme.final_theme_id}-quote-{index}",
                        review_id_hash=review.review_id_hash,
                        theme_id=final_theme.final_theme_id,
                        theme_name=final_theme.final_theme_name,
                        source=review.source,
                        rating=review.rating,
                        review_date=review.review_date,
                        quote_text=self._build_quote_text(review.review_text),
                    )
                )
        return candidates

    @staticmethod
    def _select_priority_final_themes(final_themes: list[FinalTheme]) -> list[FinalTheme]:
        ranked = sorted(
            final_themes,
            key=lambda theme: (
                theme.priority_rank or 999,
                -len(theme.supporting_review_ids),
                theme.final_theme_name.lower(),
            ),
        )
        return ranked[:MAX_TOP_THEMES]

    def _filter_quote_reviews_for_theme(
        self,
        theme_reviews: list[ReviewEvidence],
        final_theme: FinalTheme,
    ) -> list[ReviewEvidence]:
        if not theme_reviews:
            return []
        if final_theme.sentiment == "negative":
            aligned = [
                review for review in theme_reviews if review.rating <= NEGATIVE_RATING_MAX
            ]
            return aligned or [review for review in theme_reviews if review.rating <= 3]
        if final_theme.sentiment == "positive":
            aligned = [review for review in theme_reviews if review.rating >= POSITIVE_RATING_MIN]
            return aligned or [review for review in theme_reviews if review.rating >= 3]
        return theme_reviews

    def _select_quote_reviews_for_theme(
        self,
        theme_reviews: list[ReviewEvidence],
        final_theme: FinalTheme,
        limit: int = MAX_QUOTE_CANDIDATES_PER_THEME,
    ) -> list[ReviewEvidence]:
        filtered_reviews = self._filter_quote_reviews_for_theme(theme_reviews, final_theme)
        ranked_reviews = sorted(
            filtered_reviews or theme_reviews,
            key=lambda review: self._quote_rank_key(review, final_theme),
        )

        if final_theme.sentiment != "negative":
            return ranked_reviews[:limit]

        selected: list[ReviewEvidence] = []
        seen_ids: set[str] = set()

        for review in ranked_reviews:
            if review.rating == 2 and review.review_id_hash not in seen_ids:
                selected.append(review)
                seen_ids.add(review.review_id_hash)
                break

        for review in ranked_reviews:
            if len(selected) >= limit:
                break
            if review.review_id_hash in seen_ids:
                continue
            selected.append(review)
            seen_ids.add(review.review_id_hash)

        return selected[:limit]

    def _quote_rank_key(self, review: ReviewEvidence, final_theme: FinalTheme) -> tuple[Any, ...]:
        theme_keywords = set(
            self._extract_candidate_keywords(
                f"{final_theme.final_theme_name} {final_theme.summary}",
                limit=8,
            )
        )
        review_keywords = set(review.candidate_keywords or [])
        keyword_overlap_score = len(theme_keywords & review_keywords)
        quote_text = self._build_quote_text(review.review_text)
        quote_word_count = len(WORD_PATTERN.findall(quote_text))

        if final_theme.sentiment == "negative":
            alignment_bucket = 0 if review.rating <= NEGATIVE_RATING_MAX else 1
        elif final_theme.sentiment == "positive":
            alignment_bucket = 0 if review.rating >= POSITIVE_RATING_MIN else 1
        else:
            alignment_bucket = abs(review.rating - 3)

        return (
            alignment_bucket,
            -keyword_overlap_score,
            abs(quote_word_count - 18),
            -review.review_date.toordinal(),
            review.review_id_hash,
        )

    @staticmethod
    def _build_quote_text(review_text: str, max_length: int = 280) -> str:
        sentence = re.split(r"(?<=[.!?])\s+", review_text.strip())[0]
        quote = sentence if sentence else review_text.strip()
        if len(quote) <= max_length:
            return quote
        return quote[: max_length - 3].rstrip() + "..."

    def _build_final_note_request(
        self,
        *,
        final_themes: list[FinalTheme],
        quote_candidates: list[QuoteCandidate],
        reporting_start: date,
        reporting_end: date,
        source_mix: SourceMix,
        total_normalized_reviews: int,
        coverage_notes: list[str],
    ) -> FinalNoteRequest:
        return FinalNoteRequest(
            reporting_start_date=reporting_start,
            reporting_end_date=reporting_end,
            total_normalized_reviews=total_normalized_reviews,
            source_mix=source_mix,
            coverage_notes=coverage_notes,
            final_themes=final_themes,
            quote_candidates=quote_candidates,
        )

    @staticmethod
    def _render_discovery_system_prompt() -> str:
        return (
            "You are analyzing app reviews for Groww. Use only the provided evidence, do not "
            "invent quotes or counts, keep themes specific, and return valid JSON only."
        )

    def _render_discovery_user_prompt(self, request: DiscoveryRequest) -> str:
        payload = {
            "app": request.app_name,
            "batch_id": request.batch_id,
            "batch_type": request.batch_type,
            "source_scope": request.source_scope,
            "rating_band": request.rating_band,
            "reporting_window": {
                "start_date": request.reporting_start_date.isoformat(),
                "end_date": request.reporting_end_date.isoformat(),
            },
            "reviews": [review.model_dump(mode="json") for review in request.reviews],
            "expected_response_schema": {
                "batch_id": request.batch_id,
                "candidate_themes": [
                    {
                        "candidate_theme_id": "string",
                        "theme_name": "string",
                        "sentiment": "negative|positive|mixed",
                        "summary": "string",
                        "evidence_review_ids": ["review_id_hash"],
                        "recurrence_reason": "string",
                        "source_scope": ["app_store|play_store"],
                        "rating_band": "1-2|3|4-5|mixed",
                        "confidence_score": 0.0,
                    }
                ],
            },
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _render_consolidation_system_prompt() -> str:
        return (
            "You are consolidating candidate review themes for Groww. Use only the provided "
            "candidate themes and evidence references, merge only true overlaps, keep at most "
            "5 final themes, and return valid JSON only."
        )

    def _render_consolidation_user_prompt(self, request: ConsolidationRequest) -> str:
        payload = {
            "app": request.app_name,
            "reporting_window": {
                "start_date": request.reporting_start_date.isoformat(),
                "end_date": request.reporting_end_date.isoformat(),
            },
            "total_normalized_reviews": request.total_normalized_reviews,
            "source_mix": request.source_mix.model_dump(mode="json"),
            "coverage_notes": request.coverage_notes,
            "candidate_themes": [theme.model_dump(mode="json") for theme in request.candidate_themes],
            "expected_response_schema": {
                "final_themes": [
                    {
                        "final_theme_id": "string",
                        "final_theme_name": "string",
                        "sentiment": "negative|positive|mixed",
                        "summary": "string",
                        "supporting_candidate_theme_ids": ["candidate_theme_id"],
                        "supporting_review_ids": ["review_id_hash"],
                        "why_this_theme_matters": "string",
                        "priority_rank": 1,
                    }
                ]
            },
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _render_final_note_system_prompt() -> str:
        return (
            "You are generating a weekly Groww review advisory for senior leadership. Use only "
            "the provided final themes and quote candidates. Do not invent quotes or claims. "
            "Use the provided final_theme_name values exactly. Write in plain English for "
            "executives: short, concrete, and free of technical jargon (avoid terms like corpus, "
            "pipeline, consolidation, embeddings, or model names). Return valid JSON only."
        )

    def _render_final_note_user_prompt(self, request: FinalNoteRequest) -> str:
        payload = {
            "app": request.app_name,
            "reporting_window": {
                "start_date": request.reporting_start_date.isoformat(),
                "end_date": request.reporting_end_date.isoformat(),
            },
            "total_normalized_reviews": request.total_normalized_reviews,
            "source_mix": request.source_mix.model_dump(mode="json"),
            "coverage_notes": request.coverage_notes,
            "final_themes": [theme.model_dump(mode="json") for theme in request.final_themes],
            "quote_candidates": [
                quote.model_dump(mode="json") for quote in request.quote_candidates
            ],
            "instructions": {
                "theme_usage": (
                    "Use only the provided final_theme_name values. The final_themes list is "
                    "already the top-priority shortlist for the weekly pulse."
                ),
                "top_theme_count": MAX_TOP_THEMES,
                "quote_rules": [
                    "Choose quotes only from quote_candidates.",
                    "Each quote's theme_name must exactly match the chosen quote candidate theme_name.",
                    "Prefer one quote per theme unless evidence is genuinely insufficient.",
                ],
                "theme_bullet_rules": [
                    "For each top theme, return exactly 5 bullet_points.",
                    "Each bullet is one short leadership-ready line (max ~20 words) describing what users are experiencing or why it matters.",
                    "Bullets must be evidence-backed from the theme summary and quotes; do not invent facts.",
                    "Also return summary as one plain-language headline sentence for the theme.",
                ],
                "action_rules": [
                    "Return one action idea per top theme.",
                    "Each action linked_theme must exactly match one of the returned top theme names.",
                    "For each action, return exactly 5 bullet_points: practical steps leadership can track (no engineering jargon).",
                    "Also return action as one short headline sentence naming the recommended move.",
                ],
            },
            "expected_response_schema": {
                "opening_summary": "string",
                "top_themes": [
                    {
                        "theme_name": "string",
                        "summary": "string",
                        "bullet_points": ["string (exactly 5 items)"],
                        "linked_final_theme_id": "string",
                    }
                ],
                "user_quotes": [
                    {
                        "quote": "string",
                        "review_id_hash": "review_id_hash",
                        "theme_name": "string",
                    }
                ],
                "action_ideas": [
                    {
                        "action": "string",
                        "bullet_points": ["string (exactly 5 items)"],
                        "linked_theme": "string",
                    }
                ],
                "coverage_note": "string",
            },
        }
        return json.dumps(payload, indent=2)

    @staticmethod
    def _validate_final_weekly_pulse(
        *,
        weekly_pulse: WeeklyPulseResponse,
        final_note_request: FinalNoteRequest,
    ) -> None:
        available_quote_ids = {candidate.review_id_hash for candidate in final_note_request.quote_candidates}
        available_theme_names = {theme.final_theme_name for theme in final_note_request.final_themes}
        theme_id_to_name = {
            theme.final_theme_id: theme.final_theme_name for theme in final_note_request.final_themes
        }
        quote_theme_lookup: dict[str, set[str]] = defaultdict(set)
        for candidate in final_note_request.quote_candidates:
            quote_theme_lookup[candidate.review_id_hash].add(candidate.theme_name)
        selected_top_theme_names: set[str] = set()

        for theme in weekly_pulse.top_themes:
            if theme.linked_final_theme_id and theme.linked_final_theme_id not in theme_id_to_name:
                raise Phase2Error(
                    f"Weekly pulse referenced unknown top theme id: {theme.linked_final_theme_id}"
                )
            expected_theme_name = (
                theme_id_to_name.get(theme.linked_final_theme_id)
                if theme.linked_final_theme_id
                else theme.theme_name
            )
            if expected_theme_name != theme.theme_name:
                raise Phase2Error(
                    "Weekly pulse top theme name did not match the linked final theme identifier."
                )
            if theme.theme_name not in available_theme_names:
                raise Phase2Error(
                    f"Weekly pulse referenced unknown top theme name: {theme.theme_name}"
                )
            selected_top_theme_names.add(theme.theme_name)
            if len(theme.bullet_points) != 5:
                raise Phase2Error(
                    f"Top theme '{theme.theme_name}' must include exactly 5 bullet_points."
                )

        for quote in weekly_pulse.user_quotes:
            if quote.review_id_hash not in available_quote_ids:
                raise Phase2Error(
                    f"Weekly pulse referenced unknown quote review_id_hash: {quote.review_id_hash}"
                )
            if quote.theme_name not in selected_top_theme_names:
                raise Phase2Error(
                    f"Weekly pulse quote referenced a theme outside the selected top themes: {quote.theme_name}"
                )
            expected_quote_themes = quote_theme_lookup.get(quote.review_id_hash, set())
            if quote.theme_name not in expected_quote_themes:
                raise Phase2Error(
                    "Weekly pulse quote theme_name did not match the provided quote candidate theme."
                )

        for action in weekly_pulse.action_ideas:
            if action.linked_theme not in selected_top_theme_names:
                raise Phase2Error(
                    f"Weekly pulse action linked outside the selected top themes: {action.linked_theme}"
                )
            if len(action.bullet_points) != 5:
                raise Phase2Error(
                    f"Action for '{action.linked_theme}' must include exactly 5 bullet_points."
                )

    def _load_coverage_notes(
        self,
        phase1_metadata: dict[str, Any],
        phase1_metadata_path: Path,
    ) -> list[str]:
        notes = list(phase1_metadata.get("warnings", []))
        input_paths = phase1_metadata.get("inputs", {})
        app_store_input = input_paths.get("app_store_csv")
        if not app_store_input:
            return notes
        app_store_path = self._resolve_phase1_input_path(Path(app_store_input), phase1_metadata_path)
        manifest_path = app_store_path.parent / "fetch_manifest.json"
        if not manifest_path.exists():
            return notes
        manifest = self._load_json(manifest_path)
        for source_name, source_details in (manifest.get("sources") or {}).items():
            for warning in source_details.get("warnings", []):
                notes.append(f"{source_name}: {warning}")
        return notes

    @staticmethod
    def _resolve_phase1_input_path(raw_path: Path, phase1_metadata_path: Path) -> Path:
        if raw_path.is_absolute() and raw_path.exists():
            return raw_path
        if raw_path.exists():
            return raw_path
        phase1_root = phase1_metadata_path.parents[2]
        candidate = phase1_root / raw_path
        return candidate

    @staticmethod
    def _estimate_call_tokens(system_prompt: str, user_prompt: str, response_tokens: int) -> int:
        prompt_tokens = max(1, (len(system_prompt) + len(user_prompt)) // 4)
        return prompt_tokens + response_tokens

    def _estimate_total_run_tokens(self, discovery_prompts: list[dict[str, Any]]) -> int:
        discovery_tokens = sum(
            self._estimate_call_tokens(
                prompt["system_prompt"],
                prompt["user_prompt"],
                MAX_DISCOVERY_RESPONSE_TOKENS,
            )
            for prompt in discovery_prompts
        )
        return (
            discovery_tokens
            + MAX_CONSOLIDATION_RESPONSE_TOKENS
            + MAX_FINAL_NOTE_RESPONSE_TOKENS
        )

    def _write_phase2_artifacts(
        self,
        *,
        output_dir: Path,
        run_id: str,
        prepared_reviews: list[ReviewEvidence],
        working_reviews: list[ReviewEvidence],
        discovery_requests: list[DiscoveryRequest],
        discovery_prompts: list[dict[str, Any]],
        metadata: dict[str, Any],
    ) -> dict[str, str]:
        run_dir = output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        prepared_reviews_path = run_dir / "prepared_review_evidence.json"
        working_reviews_path = run_dir / "working_review_set.json"
        discovery_requests_path = run_dir / "discovery_requests.json"
        discovery_prompts_path = run_dir / "discovery_prompts.json"
        run_metadata_path = run_dir / "run_metadata.json"

        self._write_json(
            prepared_reviews_path,
            [review.model_dump(mode="json") for review in prepared_reviews],
        )
        self._write_json(
            working_reviews_path,
            [review.model_dump(mode="json") for review in working_reviews],
        )
        self._write_json(
            discovery_requests_path,
            [request.model_dump(mode="json") for request in discovery_requests],
        )
        self._write_json(discovery_prompts_path, discovery_prompts)
        self._write_json(run_metadata_path, metadata)

        return {
            "run_directory": str(run_dir),
            "prepared_review_evidence": str(prepared_reviews_path),
            "working_review_set": str(working_reviews_path),
            "discovery_requests": str(discovery_requests_path),
            "discovery_prompts": str(discovery_prompts_path),
            "run_metadata": str(run_metadata_path),
        }

    @staticmethod
    def _write_json(path: Path, payload: Any) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    @staticmethod
    def _rewrite_metadata_file(path: str, metadata: dict[str, Any]) -> None:
        Path(path).write_text(json.dumps(metadata, indent=2), encoding="utf-8")


def extract_json_object(raw_text: str) -> dict[str, Any]:
    text = raw_text.strip()
    if not text:
        raise Phase2Error("Groq returned an empty response.")

    if text.startswith("```"):
        text = JSON_FENCE_PATTERN.sub("", text).strip()

    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start == -1 or end == -1 or end <= start:
            raise Phase2Error("Could not extract a JSON object from the Groq response.")
        try:
            parsed = json.loads(text[start : end + 1])
        except json.JSONDecodeError as exc:
            raise Phase2Error("Groq response did not contain valid JSON.") from exc

    if not isinstance(parsed, dict):
        raise Phase2Error("Groq response must contain a JSON object at the top level.")
    return parsed


def _normalize_groq_structured_output(payload: Any) -> Any:
    dedupe_keys = {
        "evidence_review_ids",
        "supporting_candidate_theme_ids",
        "supporting_review_ids",
        "source_scope",
    }
    if isinstance(payload, list):
        return [_normalize_groq_structured_output(item) for item in payload]
    if not isinstance(payload, dict):
        return payload

    normalized: dict[str, Any] = {}
    for key, value in payload.items():
        normalized_value = _normalize_groq_structured_output(value)
        if key in dedupe_keys and isinstance(normalized_value, list):
            normalized_value = _dedupe_preserving_order(normalized_value)
        normalized[key] = normalized_value
    return normalized


def _dedupe_preserving_order(values: list[Any]) -> list[Any]:
    deduped: list[Any] = []
    seen: set[str] = set()
    for value in values:
        marker = json.dumps(value, sort_keys=True) if isinstance(value, (dict, list)) else repr(value)
        if marker in seen:
            continue
        seen.add(marker)
        deduped.append(value)
    return deduped


def _load_local_env_files() -> None:
    candidates = [
        Path.cwd() / ".env",
        Path(__file__).resolve().parents[1] / ".env",
        Path(__file__).resolve().parents[2] / ".env",
    ]
    seen_paths: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen_paths or not candidate.exists():
            continue
        seen_paths.add(resolved)
        _load_env_file(candidate)


def _load_env_file(path: Path) -> None:
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key:
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"\"", "'"}:
            value = value[1:-1]
        os.environ.setdefault(key, value)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 2 Groq analysis pipeline for the Review Advisory Agent."
    )
    parser.add_argument(
        "--normalized-reviews",
        type=Path,
        help="Path to the Phase 1 normalized_reviews.json file.",
    )
    parser.add_argument(
        "--phase1-metadata",
        type=Path,
        help="Optional path to the matching Phase 1 run_metadata.json file.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory where Phase 2 artifacts will be written.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Prepare deterministic artifacts and rendered prompts without calling Groq.",
    )
    parser.add_argument(
        "--groq-model",
        default=DEFAULT_GROQ_MODEL,
        help="Groq model name for live runs.",
    )
    parser.add_argument(
        "--print-schemas",
        action="store_true",
        help="Print the Phase 2 JSON schema bundle and exit.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)

    if args.print_schemas:
        from .models import dump_schema_bundle

        print(dump_schema_bundle())
        return 0

    if not args.normalized_reviews:
        parser.error("--normalized-reviews is required unless --print-schemas is used.")

    pipeline = Phase2Pipeline()
    result = pipeline.execute(
        normalized_reviews_path=args.normalized_reviews,
        phase1_metadata_path=args.phase1_metadata,
        output_dir=args.output_dir,
        dry_run=args.dry_run,
        groq_model=args.groq_model,
    )
    print(json.dumps({"metadata": result.metadata, "output_paths": result.output_paths}, indent=2))
    status = result.metadata.get("status", "")
    if status in {"completed", "dry_run_prepared"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
