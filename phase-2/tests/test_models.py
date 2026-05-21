import json
import unittest
from datetime import date

from pydantic import ValidationError

from review_advisory_phase2 import (
    CandidateTheme,
    ConsolidationResponse,
    DiscoveryRequest,
    DiscoveryResponse,
    FinalTheme,
    ReviewEvidence,
    WeeklyActionIdea,
    WeeklyPulseResponse,
    WeeklyQuote,
    WeeklyThemeSummary,
    build_schema_bundle,
)


class Phase2ContractModelTests(unittest.TestCase):
    def test_discovery_request_accepts_valid_evidence(self) -> None:
        request = DiscoveryRequest(
            batch_id="playstore-low-rating-batch-001",
            batch_type="complaint_slice",
            source_scope=["play_store"],
            rating_band="1-2",
            reporting_start_date=date(2026, 3, 16),
            reporting_end_date=date(2026, 5, 11),
            reviews=[
                ReviewEvidence(
                    review_id_hash="a" * 64,
                    source="play_store",
                    rating=1,
                    review_date=date(2026, 5, 2),
                    title="",
                    review_text="Charts are slow during market hours and order refresh keeps lagging badly.",
                    word_count=12,
                    candidate_keywords=["charts", "lag", "orders"],
                )
            ],
        )

        self.assertEqual(request.app_name, "Groww")
        self.assertEqual(request.reviews[0].source, "play_store")

    def test_discovery_response_limits_candidate_theme_count(self) -> None:
        with self.assertRaises(ValidationError):
            DiscoveryResponse(
                batch_id="batch-001",
                candidate_themes=[
                    self._candidate_theme(f"candidate-{index}", f"Theme {index}")
                    for index in range(6)
                ],
            )

    def test_candidate_theme_rejects_duplicate_evidence_ids(self) -> None:
        with self.assertRaises(ValidationError):
            CandidateTheme(
                candidate_theme_id="candidate-001",
                theme_name="Slow charts",
                sentiment="negative",
                summary="Users report lag during market movement.",
                evidence_review_ids=["a" * 64, "a" * 64],
                recurrence_reason="The same problem appears across many low-rating reviews.",
            )

    def test_consolidation_response_limits_final_themes(self) -> None:
        with self.assertRaises(ValidationError):
            ConsolidationResponse(
                final_themes=[
                    self._final_theme(f"final-{index}", f"Final Theme {index}")
                    for index in range(6)
                ]
            )

    def test_weekly_pulse_response_enforces_top_theme_quote_action_limits(self) -> None:
        with self.assertRaises(ValidationError):
            WeeklyPulseResponse(
                opening_summary="This week users discussed performance, support, and pricing concerns.",
                top_themes=[
                    WeeklyThemeSummary(
                        theme_name=f"Theme {index}",
                        summary="Summary text for validation.",
                        bullet_points=self._executive_bullets(f"Theme {index}"),
                    )
                    for index in range(4)
                ],
                user_quotes=[
                    WeeklyQuote(
                        quote="Quote text",
                        review_id_hash=f"{index:x}".rjust(64, "a"),
                        theme_name="Theme 1",
                    )
                    for index in range(3)
                ],
                action_ideas=[
                    WeeklyActionIdea(
                        action="Action text for leadership review.",
                        linked_theme="Theme 1",
                        bullet_points=self._executive_bullets("Action"),
                    )
                    for _ in range(3)
                ],
            )

    def test_schema_bundle_contains_expected_models(self) -> None:
        schema_bundle = build_schema_bundle()
        self.assertIn("DiscoveryRequest", schema_bundle)
        self.assertIn("ConsolidationResponse", schema_bundle)
        self.assertIn("WeeklyPulseResponse", schema_bundle)
        self.assertEqual(schema_bundle["ReviewEvidence"]["type"], "object")

    def test_schema_bundle_is_json_serializable(self) -> None:
        schema_bundle = build_schema_bundle()
        rendered = json.dumps(schema_bundle)
        self.assertIsInstance(rendered, str)

    @staticmethod
    def _executive_bullets(seed: str) -> list[str]:
        return [
            f"{seed}: Customers wait too long for support to resolve account issues.",
            f"{seed}: Users report orders freezing during active market sessions.",
            f"{seed}: Reviewers say fees feel higher than competing trading apps.",
            f"{seed}: Low ratings mention crashes after recent app updates.",
            f"{seed}: Trust drops when payouts or statements look unclear.",
        ]

    @staticmethod
    def _candidate_theme(theme_id: str, theme_name: str) -> CandidateTheme:
        return CandidateTheme(
            candidate_theme_id=theme_id,
            theme_name=theme_name,
            sentiment="negative",
            summary="Users repeatedly describe the same issue.",
            evidence_review_ids=["b" * 64],
            recurrence_reason="Appears repeatedly in low-rating slices.",
        )

    @staticmethod
    def _final_theme(theme_id: str, theme_name: str) -> FinalTheme:
        return FinalTheme(
            final_theme_id=theme_id,
            final_theme_name=theme_name,
            sentiment="negative",
            summary="This final theme groups related complaint evidence.",
            supporting_candidate_theme_ids=["candidate-001"],
            supporting_review_ids=["c" * 64],
            why_this_theme_matters="It directly affects trading confidence and platform trust.",
            priority_rank=1,
        )


if __name__ == "__main__":
    unittest.main()
