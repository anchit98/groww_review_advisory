from __future__ import annotations

import json
import tempfile
import unittest
from datetime import date, datetime, timezone
from pathlib import Path

from review_advisory_phase1.pipeline import CanonicalReview, PipelineRunResult
from review_advisory_phase1.warehouse import (
    load_review_dicts,
    merge_incremental_run,
    warehouse_paths,
)


def _review(review_id_hash: str, review_date: str) -> CanonicalReview:
    return CanonicalReview(
        source="play_store",
        rating=2,
        title="",
        review_text="this is a long enough english review for testing purposes",
        review_date=date.fromisoformat(review_date),
        language="en",
        ingested_at=datetime(2026, 5, 10, tzinfo=timezone.utc),
        review_id_hash=review_id_hash,
    )


class WarehouseTests(unittest.TestCase):
    def test_merge_adds_new_and_prunes_old(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            warehouse_dir = Path(tmp) / "warehouse"
            paths = warehouse_paths(warehouse_dir)
            paths["root"].mkdir(parents=True)
            paths["reviews"].write_text(
                json.dumps(
                    [
                        _review("a" * 63 + "1", "2026-02-01").to_dict(),
                        _review("b" * 63 + "2", "2026-05-05").to_dict(),
                    ]
                ),
                encoding="utf-8",
            )

            run_result = PipelineRunResult(
                normalized_reviews=[_review("c" * 63 + "3", "2026-05-10")],
                metadata={
                    "run_id": "phase1-test",
                    "status": "completed",
                    "reporting_window": {
                        "start_date": "2026-05-03",
                        "end_date": "2026-05-10",
                        "lookback_weeks": 1,
                    },
                    "assumptions": {},
                },
                output_paths={},
            )

            merged = merge_incremental_run(
                run_result=run_result,
                run_date=date(2026, 5, 10),
                warehouse_dir=warehouse_dir,
                rolling_window_weeks=8,
            )

            stored = load_review_dicts(paths["reviews"])
            hashes = {row["review_id_hash"] for row in stored}
            self.assertIn("c" * 63 + "3", hashes)
            self.assertIn("b" * 63 + "2", hashes)
            self.assertNotIn("a" * 63 + "1", hashes)
            self.assertEqual(merged.metadata["warehouse"]["new_reviews_this_run"], 1)
            self.assertEqual(merged.metadata["reporting_window"]["lookback_weeks"], 8)


if __name__ == "__main__":
    unittest.main()
