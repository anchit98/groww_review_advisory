import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

from review_advisory_phase3 import Phase3Error, Phase3Pipeline
from review_advisory_phase3.note_renderer import (
    build_google_doc_url,
    render_email_teaser,
    render_weekly_pulse_markdown,
)
from review_advisory_phase3.mcp_http_client import MCPHttpError, interpret_mcp_response
from review_advisory_phase3.validation import PublicationValidationError, assert_no_obvious_pii, validate_weekly_pulse_shape


class Phase3Tests(unittest.TestCase):
    def test_render_weekly_pulse_markdown_includes_sections(self) -> None:
        pulse = {
            "opening_summary": "Summary line with enough content.",
            "top_themes": [{"theme_name": "T1", "summary": "S1", "linked_final_theme_id": "id1"}],
            "user_quotes": [{"quote": "Q1", "review_id_hash": "a" * 64, "theme_name": "T1"}],
            "action_ideas": [{"action": "A1", "linked_theme": "T1"}],
            "coverage_note": "Coverage note.",
        }
        md = render_weekly_pulse_markdown(pulse, title="Title", reporting_label="2026-01-01 to 2026-01-07")
        self.assertIn("# Title", md)
        self.assertIn("## Top themes", md)
        self.assertIn("## Representative quotes", md)
        self.assertIn("## Action ideas", md)
        self.assertIn("Coverage note.", md)

    def test_email_teaser_is_short_and_includes_doc_link(self) -> None:
        pulse = {
            "opening_summary": "Users report support and stability issues this week.",
            "top_themes": [{"theme_name": "Support", "summary": "Long doc-only summary."}],
            "user_quotes": [{"quote": "Quote text here.", "review_id_hash": "e" * 64, "theme_name": "Support"}],
            "action_ideas": [{"action": "Improve support SLAs.", "linked_theme": "Support"}],
            "coverage_note": "App Store coverage is partial.",
        }
        doc_id = "abc123XYZ"
        teaser = render_email_teaser(
            pulse,
            reporting_label="2026-03-26 to 2026-05-21",
            google_doc_url=build_google_doc_url(doc_id),
        )
        self.assertIn(build_google_doc_url(doc_id), teaser)
        self.assertIn("Top themes:", teaser)
        self.assertNotIn("## Representative quotes", teaser)
        self.assertNotIn("review `", teaser)

    def test_validate_rejects_missing_field(self) -> None:
        with self.assertRaises(PublicationValidationError):
            validate_weekly_pulse_shape({"opening_summary": "x"})

    def test_interpret_mcp_response_raises_on_error_status(self) -> None:
        with self.assertRaises(MCPHttpError) as ctx:
            interpret_mcp_response(
                {"status": "error", "message": "Unexpected error occurred", "details": "invalid_grant"},
                operation="append_to_doc",
            )
        self.assertIn("invalid_grant", str(ctx.exception))

    def test_pii_detection_email(self) -> None:
        with self.assertRaises(PublicationValidationError):
            assert_no_obvious_pii("Contact me at user@example.com please")

    def test_dry_run_writes_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pulse_path = tmp_path / "weekly_pulse.json"
            pulse_path.write_text(
                json.dumps(
                    {
                        "opening_summary": "Opening with more than trivial length for validation.",
                        "top_themes": [{"theme_name": "T", "summary": "S"}],
                        "user_quotes": [{"quote": "Quote text here.", "review_id_hash": "b" * 64, "theme_name": "T"}],
                        "action_ideas": [{"action": "Do something useful.", "linked_theme": "T"}],
                        "coverage_note": "",
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            out = tmp_path / "p3-out"
            result = Phase3Pipeline().execute(
                weekly_pulse_path=pulse_path,
                output_dir=out,
                dry_run=True,
            )
            self.assertEqual(result.metadata["status"], "dry_run_prepared")
            self.assertTrue(Path(result.output_paths["weekly_note_markdown"]).exists())

    def test_live_requires_doc_and_recipient(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pulse_path = tmp_path / "weekly_pulse.json"
            pulse_path.write_text(
                json.dumps(
                    {
                        "opening_summary": "Opening with more than trivial length for validation.",
                        "top_themes": [{"theme_name": "T", "summary": "S"}],
                        "user_quotes": [{"quote": "Quote text here.", "review_id_hash": "c" * 64, "theme_name": "T"}],
                        "action_ideas": [{"action": "Do something useful.", "linked_theme": "T"}],
                    }
                ),
                encoding="utf-8",
            )
            with self.assertRaises(Phase3Error):
                Phase3Pipeline().execute(
                    weekly_pulse_path=pulse_path,
                    output_dir=tmp_path / "out",
                    dry_run=False,
                    google_doc_id="",
                    gmail_draft_to="",
                )

    def test_partial_failure_after_doc_raises_phase3_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            pulse_path = tmp_path / "weekly_pulse.json"
            pulse_path.write_text(
                json.dumps(
                    {
                        "opening_summary": "Opening with more than trivial length for validation.",
                        "top_themes": [{"theme_name": "T", "summary": "S"}],
                        "user_quotes": [{"quote": "Quote text here.", "review_id_hash": "d" * 64, "theme_name": "T"}],
                        "action_ideas": [{"action": "Do something useful.", "linked_theme": "T"}],
                    }
                ),
                encoding="utf-8",
            )
            out = tmp_path / "p3-live"
            with patch(
                "review_advisory_phase3.pipeline.GoogleMCPHttpClient"
            ) as mock_cls:
                inst = MagicMock()
                inst.append_to_doc.return_value = {"status": "success", "message": "Content appended"}
                from review_advisory_phase3.mcp_http_client import MCPHttpError

                captured: dict[str, str] = {}

                def _capture_draft(**kwargs: object) -> dict[str, bool]:
                    captured.update({k: str(v) for k, v in kwargs.items()})
                    raise MCPHttpError("gmail down")

                inst.create_email_draft.side_effect = _capture_draft
                mock_cls.return_value = inst
                with self.assertRaises(Phase3Error):
                    Phase3Pipeline().execute(
                        weekly_pulse_path=pulse_path,
                        output_dir=out,
                        dry_run=False,
                        mcp_base_url="https://example.invalid",
                        google_doc_id="doc123",
                        gmail_draft_to="ops@example.com",
                    )
                self.assertIn("docs.google.com/document/d/doc123", captured.get("body", ""))
                self.assertNotIn("## Representative quotes", captured.get("body", ""))
            meta_path = sorted(
                (p for p in out.iterdir() if p.is_dir()),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )[0] / "run_metadata.json"
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self.assertEqual(meta["publication"]["google_doc"]["status"], "success")
            self.assertEqual(meta["publication"]["gmail_draft"]["status"], "failed")


if __name__ == "__main__":
    unittest.main()
