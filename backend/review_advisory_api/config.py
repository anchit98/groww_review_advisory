from __future__ import annotations

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_root() -> Path:
    return Path(os.environ.get("REVIEW_ADVISORY_REPO_ROOT", _REPO_ROOT)).resolve()


def history_dir() -> Path:
    return Path(os.environ.get("REVIEW_ADVISORY_HISTORY_DIR", repo_root() / "data" / "history")).resolve()


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]
