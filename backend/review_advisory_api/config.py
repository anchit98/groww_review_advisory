from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_ROOT = Path(__file__).resolve().parents[2]
_DEFAULT_REPO_ROOT = _PACKAGE_ROOT
_RUNS_INDEX_REL = Path("data") / "history" / "runs_index.json"


def _runs_index_at(root: Path) -> Path:
    return (root / _RUNS_INDEX_REL).resolve()


def _discover_repo_root() -> Path:
    """Pick a repo root where data/history/runs_index.json exists."""
    candidates: list[Path] = []

    env_root = os.environ.get("REVIEW_ADVISORY_REPO_ROOT", "").strip()
    if env_root:
        resolved = Path(env_root).resolve()
        candidates.extend([resolved, resolved.parent])

    env_history = os.environ.get("REVIEW_ADVISORY_HISTORY_DIR", "").strip()
    if env_history:
        hist = Path(env_history).resolve()
        candidates.extend([hist.parent.parent, hist.parent])

    candidates.extend(
        [
            _DEFAULT_REPO_ROOT,
            _DEFAULT_REPO_ROOT.parent,
            Path.cwd().resolve(),
            Path.cwd().resolve().parent,
            Path("/opt/render/project/src"),
        ]
    )

    seen: set[Path] = set()
    for root in candidates:
        if root in seen:
            continue
        seen.add(root)
        if _runs_index_at(root).exists():
            return root

    if env_root:
        return Path(env_root).resolve()
    return _DEFAULT_REPO_ROOT.resolve()


def _discover_history_dir() -> Path:
    env_history = os.environ.get("REVIEW_ADVISORY_HISTORY_DIR", "").strip()
    if env_history:
        hist = Path(env_history).resolve()
        if (hist / "runs_index.json").exists():
            return hist

    root = _discover_repo_root()
    default = (root / "data" / "history").resolve()
    if (default / "runs_index.json").exists():
        return default

    for hist in (
        default,
        Path("/opt/render/project/src/data/history"),
        (_PACKAGE_ROOT / "data" / "history").resolve(),
    ):
        if (hist / "runs_index.json").exists():
            return hist.resolve()

    if env_history:
        return Path(env_history).resolve()
    return default


_REPO_ROOT = _discover_repo_root()
_HISTORY_DIR = _discover_history_dir()


def repo_root() -> Path:
    return _REPO_ROOT


def history_dir() -> Path:
    return _HISTORY_DIR


def cors_origins() -> list[str]:
    raw = os.environ.get(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    return [origin.strip() for origin in raw.split(",") if origin.strip()]


def deployment_diagnostics() -> dict[str, object]:
    index_path = history_dir() / "runs_index.json"
    return {
        "repo_root": str(repo_root()),
        "history_dir": str(history_dir()),
        "runs_index_path": str(index_path),
        "runs_index_exists": index_path.exists(),
        "review_advisory_repo_root_env": os.environ.get("REVIEW_ADVISORY_REPO_ROOT"),
        "review_advisory_history_dir_env": os.environ.get("REVIEW_ADVISORY_HISTORY_DIR"),
    }
