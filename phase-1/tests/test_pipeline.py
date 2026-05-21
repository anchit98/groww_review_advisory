import csv
import tempfile
import unittest
from datetime import date
from pathlib import Path

from review_advisory_phase1 import ReviewIngestionPipeline


class ReviewIngestionPipelineTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pipeline = ReviewIngestionPipeline()
        self.run_date = date(2026, 5, 11)

    def test_ingests_both_sources_into_canonical_schema(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_path = temp_path / "app.csv"
            play_path = temp_path / "play.csv"

            self._write_csv(
                app_path,
                ["review_id", "title", "review", "rating", "date", "language"],
                [
                    [
                        "app-1",
                        "KYC delay",
                        "Please help fix my KYC issue today test@example.com",
                        "1",
                        "2026-05-05",
                        "en",
                    ],
                    [
                        "app-2",
                        "Smooth login",
                        "The login flow is very clean and smooth now.",
                        "5",
                        "2026-04-15",
                        "en",
                    ],
                ],
            )
            self._write_csv(
                play_path,
                ["reviewId", "title", "content", "score", "at", "language"],
                [
                    [
                        "play-1",
                        "Payment issue",
                        "UPI payment failed twice and account 1234567890 is still blocked.",
                        "2",
                        "2026-05-03",
                        "en",
                    ],
                    ["play-2", "", "App feels faster after the latest update today 😊", "5", "2026-04-02", "en"],
                ],
            )

            result = self.pipeline.execute(
                app_store_csv=app_path,
                play_store_csv=play_path,
                output_dir=temp_path / "output",
                run_date=self.run_date,
                min_reviews_for_confidence=1,
            )

            self.assertEqual(result.metadata["status"], "completed")
            self.assertEqual(len(result.normalized_reviews), 4)
            self.assertTrue(result.output_paths["normalized_reviews"].endswith("normalized_reviews.json"))
            self.assertEqual(result.metadata["totals"]["normalized_rows"], 4)
            self.assertEqual(
                {review.source for review in result.normalized_reviews},
                {"app_store", "play_store"},
            )
            for review in result.normalized_reviews:
                payload = review.to_dict()
                self.assertEqual(
                    sorted(payload.keys()),
                    sorted(
                        [
                            "source",
                            "rating",
                            "title",
                            "review_text",
                            "review_date",
                            "language",
                            "ingested_at",
                            "review_id_hash",
                        ]
                    ),
                )
                self.assertEqual(len(review.review_id_hash), 64)

            sanitized_texts = [review.review_text for review in result.normalized_reviews]
            self.assertTrue(any("[REDACTED_EMAIL]" in text for text in sanitized_texts))
            self.assertTrue(any("[REDACTED_LONG_NUMERIC_ID]" in text for text in sanitized_texts))
            self.assertTrue(all("😊" not in text for text in sanitized_texts))
            self.assertTrue(all(review.language == "en" for review in result.normalized_reviews))

    def test_drops_invalid_rows_and_outside_window(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_path = temp_path / "app.csv"

            self._write_csv(
                app_path,
                ["review_id", "title", "review", "rating", "date", "language"],
                [
                    ["app-1", "Valid", "Working well now after the latest update rollout.", "4", "2026-05-04", "en"],
                    ["app-2", "Missing text", "", "2", "2026-05-02", "en"],
                    ["app-3", "Bad rating", "Rating is not valid.", "7", "2026-05-01", "en"],
                    ["app-4", "Old review", "This is too old.", "1", "2025-12-01", "en"],
                ],
            )

            result = self.pipeline.execute(
                app_store_csv=app_path,
                run_date=self.run_date,
                min_reviews_for_confidence=1,
            )

            stats = result.metadata["source_stats"]["app_store"]
            self.assertEqual(len(result.normalized_reviews), 1)
            self.assertEqual(stats["dropped_missing_required"], 1)
            self.assertEqual(stats["dropped_invalid_rating"], 1)
            self.assertEqual(stats["dropped_outside_window"], 1)

    def test_deduplicates_reviews_using_stable_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            play_path = temp_path / "play.csv"

            self._write_csv(
                play_path,
                ["reviewId", "title", "content", "score", "at", "language"],
                [
                    ["play-1", "Payment issue", "UPI payment failed twice and money is still pending.", "2", "2026-05-03", "en"],
                    ["play-1", "Payment issue duplicate", "UPI payment failed twice and money is still pending.", "2", "2026-05-03", "en"],
                ],
            )

            result = self.pipeline.execute(
                play_store_csv=play_path,
                run_date=self.run_date,
                min_reviews_for_confidence=1,
            )

            stats = result.metadata["source_stats"]["play_store"]
            self.assertEqual(len(result.normalized_reviews), 1)
            self.assertEqual(stats["duplicates_removed"], 1)
            self.assertEqual(stats["normalized_rows"], 1)

    def test_fails_clearly_when_required_columns_are_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_path = temp_path / "app.csv"

            self._write_csv(
                app_path,
                ["review_id", "title", "review", "date", "language"],
                [["app-1", "Broken export", "Column drift happened during this malformed export run.", "2026-05-04", "en"]],
            )

            result = self.pipeline.execute(app_store_csv=app_path, run_date=self.run_date)

            self.assertEqual(result.metadata["status"], "failed")
            self.assertEqual(len(result.normalized_reviews), 0)
            self.assertEqual(len(result.metadata["source_failures"]), 1)
            self.assertIn("missing required columns", result.metadata["source_failures"][0]["error"])

    def test_rejects_ambiguous_slash_dates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_path = temp_path / "app.csv"

            self._write_csv(
                app_path,
                ["review_id", "title", "review", "rating", "date", "language"],
                [["app-1", "Ambiguous date", "This review should not be accepted at all.", "3", "03/04/2026", "en"]],
            )

            result = self.pipeline.execute(app_store_csv=app_path, run_date=self.run_date)

            self.assertEqual(result.metadata["status"], "failed")
            self.assertEqual(result.metadata["source_stats"]["app_store"]["dropped_invalid_date"], 1)

    def test_marks_small_datasets_as_low_confidence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            play_path = temp_path / "play.csv"

            self._write_csv(
                play_path,
                ["reviewId", "title", "content", "score", "at", "language"],
                [["play-1", "Good update", "App is noticeably smoother after the last update.", "5", "2026-05-03", "en"]],
            )

            result = self.pipeline.execute(
                play_store_csv=play_path,
                run_date=self.run_date,
                min_reviews_for_confidence=3,
            )

            self.assertEqual(result.metadata["status"], "completed_with_warnings")
            self.assertTrue(result.metadata["low_confidence"])

    def test_drops_non_english_and_short_reviews_and_strips_emojis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)
            app_path = temp_path / "app.csv"

            self._write_csv(
                app_path,
                ["review_id", "title", "review", "rating", "date", "language"],
                [
                    [
                        "app-1",
                        "Great update 😊",
                        "This app is very easy to use today and reliable 😊",
                        "5",
                        "2026-05-04",
                        "",
                    ],
                    [
                        "app-2",
                        "Hindi review",
                        "यह ऐप बहुत अच्छा है और उपयोग में आसान है",
                        "5",
                        "2026-05-04",
                        "",
                    ],
                    [
                        "app-3",
                        "Short review",
                        "Very nice app today",
                        "4",
                        "2026-05-04",
                        "en",
                    ],
                ],
            )

            result = self.pipeline.execute(
                app_store_csv=app_path,
                run_date=self.run_date,
                min_reviews_for_confidence=1,
            )

            stats = result.metadata["source_stats"]["app_store"]
            self.assertEqual(len(result.normalized_reviews), 1)
            self.assertEqual(stats["dropped_non_english"], 1)
            self.assertEqual(stats["dropped_too_short"], 1)
            self.assertGreaterEqual(stats["emojis_removed"], 2)
            retained = result.normalized_reviews[0]
            self.assertEqual(retained.language, "en")
            self.assertNotIn("😊", retained.title)
            self.assertNotIn("😊", retained.review_text)

    @staticmethod
    def _write_csv(path: Path, header: list[str], rows: list[list[str]]) -> None:
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
