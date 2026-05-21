from __future__ import annotations

import argparse
import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .mcp_http_client import GoogleMCPHttpClient, MCPHttpConfig, MCPHttpError, interpret_mcp_response
from .note_renderer import (
    build_email_subject,
    build_google_doc_url,
    render_email_teaser,
    render_weekly_pulse_markdown,
)
from .validation import (
    PublicationValidationError,
    assert_no_obvious_pii,
    substantive_word_count,
    validate_substantive_word_budget,
    validate_weekly_pulse_shape,
)

DEFAULT_MCP_BASE_URL = "https://gmail-docs-mcp.onrender.com"


class Phase3Error(RuntimeError):
    pass


@dataclass
class Phase3ExecutionResult:
    metadata: dict[str, Any]
    output_paths: dict[str, str]


class Phase3Pipeline:
    """Publish Phase 2 weekly_pulse.json via MCP HTTP server only (no Google SDK APIs)."""

    def execute(
        self,
        *,
        weekly_pulse_path: str | Path,
        output_dir: str | Path | None = None,
        phase2_metadata_path: str | Path | None = None,
        mcp_base_url: str | None = None,
        google_doc_id: str | None = None,
        gmail_draft_to: str | None = None,
        dry_run: bool = False,
        subject_prefix: str = "Groww review pulse",
        skip_publish_if_unchanged: bool = False,
    ) -> Phase3ExecutionResult:
        pulse_path = Path(weekly_pulse_path)
        raw = self._load_json(pulse_path)
        if not isinstance(raw, dict):
            raise Phase3Error("weekly_pulse.json must contain a JSON object.")

        try:
            validate_weekly_pulse_shape(raw)
        except PublicationValidationError as exc:
            raise Phase3Error(str(exc)) from exc
        try:
            validate_substantive_word_budget(raw)
        except PublicationValidationError as exc:
            raise Phase3Error(str(exc)) from exc

        phase2_meta = self._load_phase2_metadata(
            phase2_metadata_path, weekly_pulse_path=pulse_path
        )
        reporting_label, title = self._reporting_context(phase2_meta, pulse_path)

        markdown = render_weekly_pulse_markdown(
            raw,
            title=title,
            reporting_label=reporting_label,
        )
        try:
            assert_no_obvious_pii(markdown)
        except PublicationValidationError as exc:
            raise Phase3Error(str(exc)) from exc

        substantive_words = substantive_word_count(raw)

        content_sha256 = hashlib.sha256(markdown.encode("utf-8")).hexdigest()
        subject = build_email_subject(reporting_label=reporting_label, prefix=subject_prefix)

        base_url = (mcp_base_url or os.getenv("MCP_SERVER_URL") or DEFAULT_MCP_BASE_URL).rstrip("/")
        doc_id = google_doc_id or os.getenv("GOOGLE_DOC_ID") or ""
        draft_to = gmail_draft_to or os.getenv("GMAIL_DRAFT_TO") or ""
        google_doc_url = build_google_doc_url(doc_id) if doc_id.strip() else ""
        email_body = render_email_teaser(
            raw,
            reporting_label=reporting_label,
            google_doc_url=google_doc_url or "<missing-google-doc-id>",
        )
        try:
            assert_no_obvious_pii(email_body)
        except PublicationValidationError as exc:
            raise Phase3Error(str(exc)) from exc

        run_started_at = datetime.now(timezone.utc)
        run_id = f"phase3-{uuid.uuid4().hex[:10]}"

        metadata: dict[str, Any] = {
            "run_id": run_id,
            "status": "prepared" if dry_run else "running",
            "run_started_at": run_started_at.isoformat(),
            "integration_model": "mcp_http_only",
            "mcp_server_url": base_url,
            "input_paths": {"weekly_pulse": str(pulse_path.resolve())},
            "phase2_metadata_path": (
                str(Path(phase2_metadata_path).resolve()) if phase2_metadata_path else None
            ),
            "reporting_label": reporting_label,
            "content_sha256": content_sha256,
            "google_doc_url": google_doc_url or None,
            "word_budget": {
                "max_words": 250,
                "substantive_word_count": substantive_words,
                "truncated": False,
            },
            "publication": {
                "google_doc": {"status": "skipped", "detail": ""},
                "gmail_draft": {"status": "skipped", "detail": ""},
            },
        }

        output_paths: dict[str, str] = {}
        if output_dir is not None:
            output_paths = self._write_artifacts(
                Path(output_dir),
                run_id=run_id,
                markdown=markdown,
                email_body=email_body,
                metadata=metadata,
                intended_requests={
                    "append_to_doc": {"doc_id": doc_id or "<missing>", "content": markdown},
                    "create_email_draft": {
                        "to": draft_to or "<missing>",
                        "subject": subject,
                        "body": email_body,
                    },
                },
            )

        if dry_run:
            metadata["status"] = "dry_run_prepared"
            metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
            if output_paths:
                self._rewrite_metadata(Path(output_paths["run_metadata"]), metadata)
            return Phase3ExecutionResult(metadata=metadata, output_paths=output_paths)

        if skip_publish_if_unchanged and output_paths:
            prev_hash = self._read_previous_content_hash(Path(output_paths["run_directory"]).parent)
            if prev_hash == content_sha256:
                metadata["status"] = "skipped_unchanged"
                metadata["publication"]["google_doc"]["status"] = "skipped_unchanged"
                metadata["publication"]["gmail_draft"]["status"] = "skipped_unchanged"
                metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
                if output_paths:
                    self._rewrite_metadata(Path(output_paths["run_metadata"]), metadata)
                return Phase3ExecutionResult(metadata=metadata, output_paths=output_paths)

        if not doc_id.strip():
            raise Phase3Error(
                "GOOGLE_DOC_ID (or --google-doc-id) is required for live publish. "
                "The MCP server appends to an existing document; create a doc and paste its id."
            )
        if not draft_to.strip():
            raise Phase3Error("GMAIL_DRAFT_TO (or --gmail-draft-to) is required for live Gmail draft.")

        client = GoogleMCPHttpClient(MCPHttpConfig(base_url=base_url))

        doc_result: dict[str, Any] = {}
        try:
            doc_result = client.append_to_doc(doc_id=doc_id.strip(), content=markdown)
            interpret_mcp_response(doc_result, operation="append_to_doc")
            metadata["publication"]["google_doc"] = {"status": "success", "detail": json.dumps(doc_result)[:2000]}
        except MCPHttpError as exc:
            metadata["publication"]["google_doc"] = {"status": "failed", "detail": str(exc)}
            metadata["status"] = "failed"
            metadata["failure_stage"] = "google_doc"
            metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
            if output_paths:
                self._rewrite_metadata(Path(output_paths["run_metadata"]), metadata)
            raise Phase3Error(str(exc)) from exc

        try:
            mail_result = client.create_email_draft(to=draft_to.strip(), subject=subject, body=email_body)
            interpret_mcp_response(mail_result, operation="create_email_draft")
            metadata["publication"]["gmail_draft"] = {"status": "success", "detail": json.dumps(mail_result)[:2000]}
        except MCPHttpError as exc:
            metadata["publication"]["gmail_draft"] = {"status": "failed", "detail": str(exc)}
            metadata["status"] = "partial_success"
            metadata["failure_stage"] = "gmail_draft"
            metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
            if output_paths:
                self._rewrite_metadata(Path(output_paths["run_metadata"]), metadata)
            raise Phase3Error(
                "Google Doc append succeeded but Gmail draft failed. "
                f"Doc result recorded; fix Gmail/MCP and retry. Detail: {exc}"
            ) from exc

        metadata["status"] = "completed"
        metadata["run_finished_at"] = datetime.now(timezone.utc).isoformat()
        if output_paths:
            self._rewrite_metadata(Path(output_paths["run_metadata"]), metadata)
            self._write_last_content_hash(Path(output_paths["run_directory"]).parent, content_sha256)

        return Phase3ExecutionResult(metadata=metadata, output_paths=output_paths)

    @staticmethod
    def _load_json(path: Path) -> Any:
        if not path.exists():
            raise Phase3Error(f"File not found: {path}")
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise Phase3Error(f"Invalid JSON: {path}") from exc

    @staticmethod
    def _load_phase2_metadata(
        path: str | Path | None,
        *,
        weekly_pulse_path: Path,
    ) -> dict[str, Any] | None:
        candidates: list[Path] = []
        if path is not None:
            candidates.append(Path(path))
        candidates.append(weekly_pulse_path.parent / "run_metadata.json")
        for p in candidates:
            if not p.exists():
                continue
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict):
                return data
        return None

    @staticmethod
    def _reporting_context(
        phase2_meta: dict[str, Any] | None,
        weekly_pulse_path: Path,
    ) -> tuple[str, str]:
        if phase2_meta and isinstance(phase2_meta.get("reporting_window"), dict):
            rw = phase2_meta["reporting_window"]
            start = rw.get("start_date")
            end = rw.get("end_date")
            if start and end:
                label = f"{start} to {end}"
                title = f"Groww review advisory — week ending {end}"
                return label, title
        stem = weekly_pulse_path.parent.name
        return stem, f"Groww review advisory — {stem}"

    @staticmethod
    def _write_artifacts(
        output_dir: Path,
        *,
        run_id: str,
        markdown: str,
        email_body: str,
        metadata: dict[str, Any],
        intended_requests: dict[str, Any],
    ) -> dict[str, str]:
        run_dir = output_dir / run_id
        run_dir.mkdir(parents=True, exist_ok=True)
        md_path = run_dir / "weekly_note.md"
        email_path = run_dir / "email_draft.txt"
        meta_path = run_dir / "run_metadata.json"
        intent_path = run_dir / "intended_mcp_requests.json"
        md_path.write_text(markdown, encoding="utf-8")
        email_path.write_text(email_body, encoding="utf-8")
        meta_path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
        intent_path.write_text(json.dumps(intended_requests, indent=2), encoding="utf-8")
        return {
            "run_directory": str(run_dir),
            "weekly_note_markdown": str(md_path),
            "email_draft_body": str(email_path),
            "run_metadata": str(meta_path),
            "intended_mcp_requests": str(intent_path),
        }

    @staticmethod
    def _rewrite_metadata(path: Path, metadata: dict[str, Any]) -> None:
        path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    @staticmethod
    def _write_last_content_hash(output_root: Path, content_hash: str) -> None:
        """Store last successful content hash at output_root for idempotency across runs."""
        output_root.mkdir(parents=True, exist_ok=True)
        (output_root / ".phase3_last_content_sha256").write_text(content_hash, encoding="utf-8")

    @staticmethod
    def _read_previous_content_hash(output_root: Path) -> str | None:
        p = output_root / ".phase3_last_content_sha256"
        if not p.exists():
            return None
        return p.read_text(encoding="utf-8").strip() or None


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Phase 3: publish weekly pulse to Google Docs + Gmail draft via MCP HTTP server."
    )
    parser.add_argument(
        "--weekly-pulse",
        type=Path,
        required=True,
        help="Path to Phase 2 weekly_pulse.json",
    )
    parser.add_argument(
        "--phase2-metadata",
        type=Path,
        default=None,
        help="Optional Phase 2 run_metadata.json for reporting window labels.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("output"),
        help="Directory for run artifacts (markdown, metadata, intended requests).",
    )
    parser.add_argument(
        "--mcp-base-url",
        type=str,
        default=None,
        help="Override MCP server base URL (default: MCP_SERVER_URL env or hosted default).",
    )
    parser.add_argument(
        "--google-doc-id",
        type=str,
        default=None,
        help="Target Google Doc id for append_to_doc (or set GOOGLE_DOC_ID).",
    )
    parser.add_argument(
        "--gmail-draft-to",
        type=str,
        default=None,
        help="Recipient for Gmail draft (or set GMAIL_DRAFT_TO).",
    )
    parser.add_argument(
        "--subject-prefix",
        type=str,
        default="Groww review pulse",
        help="Email subject prefix before the reporting label.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render markdown and intended MCP payloads without calling the server.",
    )
    parser.add_argument(
        "--skip-publish-if-unchanged",
        action="store_true",
        help="If content hash matches last successful publish under output-dir, skip MCP calls.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_argument_parser()
    args = parser.parse_args(argv)
    pipeline = Phase3Pipeline()
    result = pipeline.execute(
        weekly_pulse_path=args.weekly_pulse,
        output_dir=args.output_dir,
        phase2_metadata_path=args.phase2_metadata,
        mcp_base_url=args.mcp_base_url,
        google_doc_id=args.google_doc_id,
        gmail_draft_to=args.gmail_draft_to,
        dry_run=args.dry_run,
        subject_prefix=args.subject_prefix,
        skip_publish_if_unchanged=args.skip_publish_if_unchanged,
    )
    print(json.dumps({"metadata": result.metadata, "output_paths": result.output_paths}, indent=2))
    status = result.metadata.get("status", "")
    if status in {"completed", "dry_run_prepared", "skipped_unchanged"}:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
