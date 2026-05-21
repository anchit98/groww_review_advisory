import json
import os
import tempfile
import unittest
from datetime import date
from pathlib import Path

from review_advisory_phase2 import FinalTheme, Phase2Error, Phase2Pipeline, extract_json_object
from review_advisory_phase2.pipeline import (
    MAX_WORKING_REVIEWS,
    NEGATIVE_RATING_MAX,
    _load_env_file,
    _normalize_groq_structured_output,
)


class Phase2PipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = Phase2Pipeline()

    def test_extract_json_object_handles_markdown_fences(self) -> None:
        payload = extract_json_object(
            """```json
            {"batch_id":"batch-001","candidate_themes":[]}
            ```"""
        )
        self.assertEqual(payload["batch_id"], "batch-001")

    def test_validate_phase1_handoff_rejects_wrong_language_assumption(self) -> None:
        reviews = [self._review("a" * 64, "play_store", 1, "Charts lag badly during market hours today.")]
        metadata = self._metadata()
        metadata["assumptions"]["normalized_review_language"] = "unknown"

        with self.assertRaises(Phase2Error):
            self.pipeline._validate_phase1_handoff(  # noqa: SLF001 - direct unit test on internal handoff gate
                reviews=reviews,
                phase1_metadata=metadata,
                normalized_reviews_path=Path("normalized_reviews.json"),
                phase1_metadata_path=Path("run_metadata.json"),
            )

    def test_build_discovery_requests_creates_source_and_rating_batches(self) -> None:
        reviews = self.pipeline._prepare_review_evidence(  # noqa: SLF001 - testing deterministic preparation
            [
                self._review("a" * 64, "app_store", 1, "Brokerage charges feel very high for simple trades today."),
                self._review("b" * 64, "play_store", 1, "Charts are slow and orders refresh too late in market hours."),
                self._review("c" * 64, "play_store", 3, "Customer support takes too much time to connect and respond."),
                self._review("d" * 64, "app_store", 5, "Very simple and reliable mutual fund investment experience overall."),
                self._review("e" * 64, "play_store", 5, "The platform is friendly for beginners and easy to understand."),
            ]
        )

        requests = self.pipeline._build_discovery_requests(  # noqa: SLF001 - testing deterministic batching
            reviews,
            reporting_start=date(2026, 3, 16),
            reporting_end=date(2026, 5, 11),
        )

        batch_ids = {request.batch_id for request in requests}
        self.assertIn("app_store-1-2-batch-001", batch_ids)
        self.assertIn("play_store-1-2-batch-001", batch_ids)
        self.assertIn("mixed-3-batch-001", batch_ids)
        self.assertIn("app_store-4-5-batch-001", batch_ids)
        self.assertIn("play_store-4-5-batch-001", batch_ids)

    def test_select_working_review_set_caps_to_1000_and_keeps_app_store(self) -> None:
        reviews = []
        for index in range(200):
            reviews.append(
                self._review(
                    f"a{index:063d}",
                    "app_store",
                    1 if index % 2 == 0 else 5,
                    f"App store review {index} describes a clear issue with recent investment app behaviour today.",
                )
            )
        for index in range(1200):
            rating = 1 if index < 700 else 5
            reviews.append(
                self._review(
                    f"b{index:063d}",
                    "play_store",
                    rating,
                    f"Play store review {index} explains repeated order flow, charting, and support issues during market hours.",
                )
            )

        prepared = self.pipeline._prepare_review_evidence(reviews)  # noqa: SLF001
        selected = self.pipeline._select_working_review_set(prepared)  # noqa: SLF001

        self.assertEqual(len(selected), MAX_WORKING_REVIEWS)
        self.assertEqual(sum(1 for review in selected if review.source == "app_store"), 200)
        self.assertGreater(sum(1 for review in selected if review.source == "play_store" and review.rating <= 2), 0)

    def test_group_reviews_by_rating_band_includes_two_star_in_complaint_slice(self) -> None:
        reviews = self.pipeline._prepare_review_evidence(  # noqa: SLF001
            [
                self._review("a" * 64, "play_store", 1, "One star complaint about slow charts today."),
                self._review("b" * 64, "play_store", 2, "Two star complaint about high brokerage charges today."),
                self._review("c" * 64, "play_store", 3, "Neutral three star review about average experience today."),
            ]
        )

        grouped = self.pipeline._group_reviews_by_rating_band(reviews)  # noqa: SLF001

        self.assertEqual(NEGATIVE_RATING_MAX, 2)
        self.assertEqual(len(grouped["1-2"]), 2)
        self.assertEqual(grouped["1-2"][0].rating, 1)
        self.assertEqual(grouped["1-2"][1].rating, 2)

    def test_select_quote_reviews_for_negative_theme_includes_two_star_when_available(self) -> None:
        one_star = self._review("a" * 64, "play_store", 1, "Brokerage charges feel very high for simple trades today.")
        two_star = self._review("b" * 64, "play_store", 2, "Brokerage is expensive compared with other brokers this week.")
        theme = FinalTheme(
            final_theme_id="theme_1",
            final_theme_name="High Brokerage Charges",
            sentiment="negative",
            summary="Users complain about high brokerage.",
            supporting_candidate_theme_ids=["candidate_1"],
            supporting_review_ids=[one_star.review_id_hash, two_star.review_id_hash],
            why_this_theme_matters="Matters for retention.",
            priority_rank=1,
        )

        selected = self.pipeline._select_quote_reviews_for_theme(  # noqa: SLF001
            [one_star, two_star],
            theme,
            limit=2,
        )

        self.assertEqual(len(selected), 2)
        self.assertIn(2, {review.rating for review in selected})

    def test_load_env_file_sets_groq_api_key_without_overriding_existing_env(self) -> None:
        previous_value = os.environ.get("GROQ_API_KEY")
        try:
            os.environ.pop("GROQ_API_KEY", None)
            with tempfile.TemporaryDirectory() as temp_dir:
                env_path = Path(temp_dir) / ".env"
                env_path.write_text(
                    '# comment\nGROQ_API_KEY="test-key-from-env-file"\n',
                    encoding="utf-8",
                )
                _load_env_file(env_path)
                self.assertEqual(os.environ.get("GROQ_API_KEY"), "test-key-from-env-file")

                os.environ["GROQ_API_KEY"] = "already-set"
                _load_env_file(env_path)
                self.assertEqual(os.environ.get("GROQ_API_KEY"), "already-set")
        finally:
            if previous_value is None:
                os.environ.pop("GROQ_API_KEY", None)
            else:
                os.environ["GROQ_API_KEY"] = previous_value

    def test_normalize_groq_structured_output_deduplicates_known_id_lists(self) -> None:
        payload = {
            "final_themes": [
                {
                    "supporting_candidate_theme_ids": ["theme-1", "theme-1", "theme-2"],
                    "supporting_review_ids": ["abc", "abc", "def"],
                    "source_scope": ["play_store", "play_store", "app_store"],
                }
            ]
        }

        normalized = _normalize_groq_structured_output(payload)

        self.assertEqual(
            normalized["final_themes"][0]["supporting_candidate_theme_ids"],
            ["theme-1", "theme-2"],
        )
        self.assertEqual(
            normalized["final_themes"][0]["supporting_review_ids"],
            ["abc", "def"],
        )
        self.assertEqual(
            normalized["final_themes"][0]["source_scope"],
            ["play_store", "app_store"],
        )

    def test_select_priority_final_themes_returns_top_three_by_rank(self) -> None:
        from review_advisory_phase2 import FinalTheme

        themes = [
            FinalTheme(
                final_theme_id=f"theme_{index}",
                final_theme_name=f"Theme {index}",
                sentiment="negative" if index < 3 else "positive",
                summary=f"Summary {index}",
                supporting_candidate_theme_ids=[f"candidate_{index}"],
                supporting_review_ids=[f"{index}" * 64],
                why_this_theme_matters=f"Why {index}",
                priority_rank=index,
            )
            for index in range(1, 6)
        ]

        selected = self.pipeline._select_priority_final_themes(themes)  # noqa: SLF001

        self.assertEqual([theme.priority_rank for theme in selected], [1, 2, 3])

    def test_validate_final_weekly_pulse_rejects_quotes_outside_selected_top_themes(self) -> None:
        from review_advisory_phase2 import FinalNoteRequest, FinalTheme, QuoteCandidate, SourceMix, WeeklyPulseResponse

        request = FinalNoteRequest(
            reporting_start_date=date(2026, 3, 16),
            reporting_end_date=date(2026, 5, 11),
            total_normalized_reviews=10,
            source_mix=SourceMix(app_store=2, play_store=8),
            final_themes=[
                FinalTheme(
                    final_theme_id="theme_1",
                    final_theme_name="Theme One",
                    sentiment="negative",
                    summary="Theme one summary",
                    supporting_candidate_theme_ids=["candidate_1"],
                    supporting_review_ids=["a" * 64],
                    why_this_theme_matters="Theme one matters",
                    priority_rank=1,
                ),
                FinalTheme(
                    final_theme_id="theme_2",
                    final_theme_name="Theme Two",
                    sentiment="negative",
                    summary="Theme two summary",
                    supporting_candidate_theme_ids=["candidate_2"],
                    supporting_review_ids=["b" * 64],
                    why_this_theme_matters="Theme two matters",
                    priority_rank=2,
                ),
                FinalTheme(
                    final_theme_id="theme_3",
                    final_theme_name="Theme Three",
                    sentiment="positive",
                    summary="Theme three summary",
                    supporting_candidate_theme_ids=["candidate_3"],
                    supporting_review_ids=["c" * 64],
                    why_this_theme_matters="Theme three matters",
                    priority_rank=3,
                ),
            ],
            quote_candidates=[
                QuoteCandidate(
                    quote_candidate_id="q1",
                    review_id_hash="a" * 64,
                    theme_id="theme_1",
                    theme_name="Theme One",
                    source="play_store",
                    rating=1,
                    review_date=date(2026, 5, 1),
                    quote_text="Theme one quote text with enough words to remain valid.",
                ),
                QuoteCandidate(
                    quote_candidate_id="q2",
                    review_id_hash="b" * 64,
                    theme_id="theme_2",
                    theme_name="Theme Two",
                    source="play_store",
                    rating=1,
                    review_date=date(2026, 5, 1),
                    quote_text="Theme two quote text with enough words to remain valid.",
                ),
                QuoteCandidate(
                    quote_candidate_id="q3",
                    review_id_hash="c" * 64,
                    theme_id="theme_3",
                    theme_name="Theme Three",
                    source="play_store",
                    rating=5,
                    review_date=date(2026, 5, 1),
                    quote_text="Theme three quote text with enough words to remain valid.",
                ),
            ],
        )

        pulse = WeeklyPulseResponse(
            opening_summary="Weekly summary with enough detail to pass validation.",
            top_themes=[
                {"theme_name": "Theme One", "summary": "Theme one summary", "linked_final_theme_id": "theme_1"},
                {"theme_name": "Theme Two", "summary": "Theme two summary", "linked_final_theme_id": "theme_2"},
            ],
            user_quotes=[
                {"quote": "Theme one quote text with enough words to remain valid.", "review_id_hash": "a" * 64, "theme_name": "Theme Three"}
            ],
            action_ideas=[
                {"action": "Investigate theme one issue in a grounded way.", "linked_theme": "Theme One"}
            ],
            coverage_note="",
        )

        with self.assertRaises(Phase2Error):
            self.pipeline._validate_final_weekly_pulse(  # noqa: SLF001
                weekly_pulse=pulse,
                final_note_request=request,
            )

    def test_dry_run_writes_phase2_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            phase1_root = temp_path / "phase-1"
            output_run_dir = phase1_root / "output" / "phase1-test-run"
            raw_run_dir = phase1_root / "data" / "raw" / "2026-05-11"
            output_run_dir.mkdir(parents=True)
            raw_run_dir.mkdir(parents=True)

            normalized_path = output_run_dir / "normalized_reviews.json"
            metadata_path = output_run_dir / "run_metadata.json"
            output_dir = temp_path / "phase2-output"

            normalized_reviews = [
                self._review_dump("a" * 64, "app_store", 1, "Brokerage charges feel very high for simple trades today."),
                self._review_dump("b" * 64, "play_store", 1, "Charts are slow and orders refresh too late in market hours."),
                self._review_dump("c" * 64, "play_store", 3, "Customer support takes too much time to connect and respond."),
                self._review_dump("d" * 64, "app_store", 5, "Very simple and reliable mutual fund investment experience overall."),
                self._review_dump("e" * 64, "play_store", 5, "The platform is friendly for beginners and easy to understand."),
            ]
            normalized_path.write_text(json.dumps(normalized_reviews, indent=2), encoding="utf-8")
            metadata_path.write_text(json.dumps(self._metadata(), indent=2), encoding="utf-8")
            (raw_run_dir / "fetch_manifest.json").write_text(
                json.dumps(
                    {
                        "sources": {
                            "app_store": {
                                "warnings": [
                                    "App Store public coverage did not reach the full requested lookback window."
                                ]
                            },
                            "play_store": {"warnings": []},
                        }
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )

            result = self.pipeline.execute(
                normalized_reviews_path=normalized_path,
                phase1_metadata_path=metadata_path,
                output_dir=output_dir,
                dry_run=True,
            )

            self.assertEqual(result.metadata["status"], "dry_run_prepared")
            self.assertTrue(any("app_store:" in note for note in result.metadata["coverage_notes"]))
            self.assertTrue(Path(result.output_paths["run_directory"]).exists())
            self.assertTrue(Path(result.output_paths["discovery_requests"]).exists())
            self.assertTrue(Path(result.output_paths["discovery_prompts"]).exists())
            self.assertTrue(Path(result.output_paths["working_review_set"]).exists())

    @staticmethod
    def _review(review_id_hash: str, source: str, rating: int, review_text: str):
        from review_advisory_phase2 import ReviewEvidence

        return ReviewEvidence(
            review_id_hash=review_id_hash,
            source=source,
            rating=rating,
            review_date=date(2026, 5, 1),
            title="",
            review_text=review_text,
        )

    @staticmethod
    def _review_dump(review_id_hash: str, source: str, rating: int, review_text: str) -> dict:
        return {
            "source": source,
            "rating": rating,
            "title": "",
            "review_text": review_text,
            "review_date": "2026-05-01",
            "language": "en",
            "ingested_at": "2026-05-11T14:09:31.581943+00:00",
            "review_id_hash": review_id_hash,
        }

    @staticmethod
    def _metadata() -> dict:
        return {
            "run_id": "phase1-2026-05-11-test",
            "status": "completed",
            "reporting_window": {
                "start_date": "2026-03-16",
                "end_date": "2026-05-11",
                "lookback_weeks": 8,
            },
            "assumptions": {
                "min_reviews_for_confidence": 5,
                "accepted_sources": ["app_store", "play_store"],
                "output_scope": "Phase 1 ingestion only",
                "normalized_review_language": "en",
                "minimum_review_word_count": 7,
                "emoji_policy": "strip emojis from retained reviews",
            },
            "inputs": {
                "app_store_csv": "data/raw/2026-05-11/groww_app_store_reviews.csv",
                "play_store_csv": "data/raw/2026-05-11/groww_play_store_reviews.csv",
            },
            "warnings": [],
        }


if __name__ == "__main__":
    unittest.main()
