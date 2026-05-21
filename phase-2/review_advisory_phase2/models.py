from __future__ import annotations

import json
from datetime import date
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator, model_validator


StoreSource = Literal["app_store", "play_store"]
Sentiment = Literal["negative", "positive", "mixed"]
RatingBand = Literal["1-2", "3", "4-5", "mixed"]

MAX_DISCOVERY_THEMES = 5
MAX_FINAL_THEMES = 5
MAX_TOP_THEMES = 3
MAX_QUOTES = 3
MAX_ACTIONS = 3
EXEC_BULLETS_PER_ITEM = 5

ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=500)]
MediumText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=2000)]
ExecutiveBullet = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=8, max_length=220),
]
LongText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=6000)]
Identifier = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=120)]
HashId = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[0-9a-f]{64}$")]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class SourceMix(StrictModel):
    app_store: int = Field(default=0, ge=0)
    play_store: int = Field(default=0, ge=0)

    @property
    def total_reviews(self) -> int:
        return self.app_store + self.play_store


class ReviewEvidence(StrictModel):
    review_id_hash: HashId
    source: StoreSource
    rating: int = Field(ge=1, le=5)
    review_date: date
    title: str = Field(default="", max_length=500)
    review_text: LongText
    slice_id: str | None = Field(default=None, max_length=120)
    word_count: int | None = Field(default=None, ge=0)
    candidate_keywords: list[str] = Field(default_factory=list, max_length=25)
    duplicate_group_id: str | None = Field(default=None, max_length=120)

    @field_validator("candidate_keywords")
    @classmethod
    def validate_candidate_keywords(cls, value: list[str]) -> list[str]:
        cleaned = [keyword.strip() for keyword in value if keyword.strip()]
        if len(cleaned) != len(set(cleaned)):
            raise ValueError("candidate_keywords must not contain duplicates.")
        return cleaned

    @model_validator(mode="after")
    def validate_word_count(self) -> "ReviewEvidence":
        if self.word_count is not None and self.word_count <= 0:
            raise ValueError("word_count must be positive when provided.")
        return self


class DiscoveryRequest(StrictModel):
    app_name: str = Field(default="Groww", frozen=True)
    batch_id: Identifier
    batch_type: Identifier
    source_scope: list[StoreSource] = Field(min_length=1)
    rating_band: RatingBand
    reporting_start_date: date
    reporting_end_date: date
    reviews: list[ReviewEvidence] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_reporting_window(self) -> "DiscoveryRequest":
        if self.reporting_start_date > self.reporting_end_date:
            raise ValueError("reporting_start_date must be on or before reporting_end_date.")
        return self


class CandidateTheme(StrictModel):
    candidate_theme_id: Identifier
    theme_name: ShortText
    sentiment: Sentiment
    summary: MediumText
    evidence_review_ids: list[HashId] = Field(min_length=1)
    recurrence_reason: MediumText
    source_scope: list[StoreSource] = Field(default_factory=list)
    rating_band: RatingBand | None = None
    confidence_score: float | None = Field(default=None, ge=0.0, le=1.0)

    @field_validator("evidence_review_ids")
    @classmethod
    def validate_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_review_ids must not contain duplicates.")
        return value


class DiscoveryResponse(StrictModel):
    batch_id: Identifier
    candidate_themes: list[CandidateTheme] = Field(min_length=1, max_length=MAX_DISCOVERY_THEMES)


class ConsolidationCandidateTheme(StrictModel):
    candidate_theme_id: Identifier
    source_batch_id: Identifier
    theme_name: ShortText
    sentiment: Sentiment
    summary: MediumText
    evidence_review_ids: list[HashId] = Field(min_length=1)
    recurrence_reason: MediumText
    source_scope: list[StoreSource] = Field(default_factory=list)
    rating_band: RatingBand | None = None
    candidate_weight: int | None = Field(default=None, ge=1)

    @field_validator("evidence_review_ids")
    @classmethod
    def validate_unique_evidence_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("evidence_review_ids must not contain duplicates.")
        return value


class ConsolidationRequest(StrictModel):
    app_name: str = Field(default="Groww", frozen=True)
    reporting_start_date: date
    reporting_end_date: date
    total_normalized_reviews: int = Field(ge=1)
    source_mix: SourceMix
    coverage_notes: list[str] = Field(default_factory=list, max_length=10)
    candidate_themes: list[ConsolidationCandidateTheme] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_total_reviews(self) -> "ConsolidationRequest":
        if self.reporting_start_date > self.reporting_end_date:
            raise ValueError("reporting_start_date must be on or before reporting_end_date.")
        if self.source_mix.total_reviews > self.total_normalized_reviews:
            raise ValueError("source_mix total cannot exceed total_normalized_reviews.")
        return self


class FinalTheme(StrictModel):
    final_theme_id: Identifier
    final_theme_name: ShortText
    sentiment: Sentiment
    summary: MediumText
    supporting_candidate_theme_ids: list[Identifier] = Field(min_length=1)
    supporting_review_ids: list[HashId] = Field(min_length=1)
    why_this_theme_matters: MediumText
    priority_rank: int | None = Field(default=None, ge=1, le=MAX_FINAL_THEMES)

    @field_validator("supporting_candidate_theme_ids", "supporting_review_ids")
    @classmethod
    def validate_unique_ids(cls, value: list[str]) -> list[str]:
        if len(value) != len(set(value)):
            raise ValueError("supporting ids must not contain duplicates.")
        return value


class ConsolidationResponse(StrictModel):
    final_themes: list[FinalTheme] = Field(min_length=1, max_length=MAX_FINAL_THEMES)


class QuoteCandidate(StrictModel):
    quote_candidate_id: Identifier
    review_id_hash: HashId
    theme_id: Identifier
    theme_name: ShortText
    source: StoreSource
    rating: int = Field(ge=1, le=5)
    review_date: date
    quote_text: MediumText


class FinalNoteRequest(StrictModel):
    app_name: str = Field(default="Groww", frozen=True)
    reporting_start_date: date
    reporting_end_date: date
    total_normalized_reviews: int = Field(ge=1)
    source_mix: SourceMix
    coverage_notes: list[str] = Field(default_factory=list, max_length=10)
    final_themes: list[FinalTheme] = Field(min_length=1, max_length=MAX_FINAL_THEMES)
    quote_candidates: list[QuoteCandidate] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_request_window(self) -> "FinalNoteRequest":
        if self.reporting_start_date > self.reporting_end_date:
            raise ValueError("reporting_start_date must be on or before reporting_end_date.")
        if self.source_mix.total_reviews > self.total_normalized_reviews:
            raise ValueError("source_mix total cannot exceed total_normalized_reviews.")
        return self


class WeeklyThemeSummary(StrictModel):
    theme_name: ShortText
    summary: MediumText
    bullet_points: list[ExecutiveBullet] = Field(
        min_length=EXEC_BULLETS_PER_ITEM,
        max_length=EXEC_BULLETS_PER_ITEM,
    )
    linked_final_theme_id: Identifier | None = None


class WeeklyQuote(StrictModel):
    quote: MediumText
    review_id_hash: HashId
    theme_name: ShortText


class WeeklyActionIdea(StrictModel):
    action: MediumText
    bullet_points: list[ExecutiveBullet] = Field(
        min_length=EXEC_BULLETS_PER_ITEM,
        max_length=EXEC_BULLETS_PER_ITEM,
    )
    linked_theme: ShortText


class WeeklyPulseResponse(StrictModel):
    opening_summary: MediumText
    top_themes: list[WeeklyThemeSummary] = Field(min_length=1, max_length=MAX_TOP_THEMES)
    user_quotes: list[WeeklyQuote] = Field(min_length=1, max_length=MAX_QUOTES)
    action_ideas: list[WeeklyActionIdea] = Field(min_length=1, max_length=MAX_ACTIONS)
    coverage_note: str = Field(default="", max_length=500)


SCHEMA_MODELS: dict[str, type[BaseModel]] = {
    "ReviewEvidence": ReviewEvidence,
    "DiscoveryRequest": DiscoveryRequest,
    "CandidateTheme": CandidateTheme,
    "DiscoveryResponse": DiscoveryResponse,
    "ConsolidationCandidateTheme": ConsolidationCandidateTheme,
    "ConsolidationRequest": ConsolidationRequest,
    "FinalTheme": FinalTheme,
    "ConsolidationResponse": ConsolidationResponse,
    "QuoteCandidate": QuoteCandidate,
    "FinalNoteRequest": FinalNoteRequest,
    "WeeklyThemeSummary": WeeklyThemeSummary,
    "WeeklyQuote": WeeklyQuote,
    "WeeklyActionIdea": WeeklyActionIdea,
    "WeeklyPulseResponse": WeeklyPulseResponse,
}


def build_schema_bundle() -> dict[str, dict]:
    return {
        model_name: model.model_json_schema()
        for model_name, model in SCHEMA_MODELS.items()
    }


def dump_schema_bundle(indent: int = 2) -> str:
    return json.dumps(build_schema_bundle(), indent=indent)
