#!/usr/bin/env python3
"""Add executive bullet_points to an existing weekly_pulse.json for UI preview."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE2_DIR = REPO_ROOT / "phase-2"
sys.path.insert(0, str(PHASE2_DIR))

BULLET_COUNT = 5


def _load_dotenv() -> None:
    env_path = REPO_ROOT / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


def _load_json(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Updated {path}")


def _clean_quote_for_bullet(text: str) -> str:
    cleaned = re.sub(r"\s+", " ", text.strip())
    if len(cleaned) <= 12:
        return cleaned
    cleaned = cleaned[0].upper() + cleaned[1:]
    if cleaned.lower().startswith(("customers", "users", "traders", "investors")):
        return cleaned if cleaned.endswith(".") else f"{cleaned}."
    return f"Users say {cleaned.rstrip('.')}."


def _bullets_from_quotes(theme_name: str, summary: str, quotes: list[str]) -> list[str]:
    bullets: list[str] = []
    seen: set[str] = set()

    for quote in quotes:
        candidate = _clean_quote_for_bullet(quote)
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(candidate)
        if len(bullets) >= BULLET_COUNT:
            return bullets

    for sentence in re.split(r"(?<=[.!?])\s+", summary):
        sentence = sentence.strip()
        if len(sentence) < 20:
            continue
        candidate = sentence if sentence.endswith(".") else f"{sentence}."
        key = candidate.lower()
        if key in seen:
            continue
        seen.add(key)
        bullets.append(candidate)
        if len(bullets) >= BULLET_COUNT:
            return bullets

    pads = [
        f"Negative reviews for {theme_name} continue to cluster in the latest reporting window.",
        f"Leadership should treat {theme_name} as a priority trust and retention risk.",
        f"Users expect faster fixes and clearer communication on {theme_name}.",
        f"Competitor apps are cited as offering a smoother experience on this topic.",
        f"Resolving {theme_name} could improve store ratings and repeat trading activity.",
    ]
    for line in pads:
        if len(bullets) >= BULLET_COUNT:
            break
        bullets.append(line)
    return bullets[:BULLET_COUNT]


def _bullets_from_action(action: str, linked_theme: str) -> list[str]:
    headline = action.rstrip(".")
    theme_short = linked_theme.split(" and ")[0].lower()
    return [
        f"Assign an executive owner to improve {theme_short} within the next two weeks.",
        f"Define three measurable outcomes tied to: {headline.lower()}.",
        "Communicate planned fixes to users through in-app updates and support macros.",
        "Track weekly progress with store rating and complaint volume as success signals.",
        "Review results in the next leadership advisory and adjust resourcing if needed.",
    ]


def _generate_with_groq(pulse: dict, quotes_by_theme: dict[str, list[str]]) -> dict | None:
    api_key = os.environ.get("GROQ_API_KEY", "").strip()
    if not api_key:
        return None

    from review_advisory_phase2.pipeline import GroqClient, GroqConfig  # noqa: PLC0415

    payload = {
        "top_themes": [
            {
                "theme_name": theme["theme_name"],
                "summary": theme["summary"],
                "sample_quotes": quotes_by_theme.get(theme["theme_name"], [])[:5],
            }
            for theme in pulse["top_themes"]
        ],
        "action_ideas": pulse["action_ideas"],
        "instructions": {
            "audience": "senior Groww leadership",
            "style": "plain English, no technical jargon, max 20 words per bullet",
            "theme_bullets_per_theme": BULLET_COUNT,
            "action_bullets_per_action": BULLET_COUNT,
            "rules": [
                "Use only provided summaries and quotes; do not invent facts.",
                "Return exactly 5 bullet_points per theme and per action.",
            ],
        },
        "expected_response": {
            "top_themes": [
                {"theme_name": "string", "bullet_points": ["string"] * BULLET_COUNT}
            ],
            "action_ideas": [
                {"linked_theme": "string", "bullet_points": ["string"] * BULLET_COUNT}
            ],
        },
    }

    system_prompt = (
        "You enrich a weekly Groww leadership advisory. Return valid JSON only. "
        "Write short executive bullet_points grounded in the evidence provided."
    )
    client = GroqClient(
        GroqConfig(
            api_key=api_key,
            model=os.environ.get("GROQ_MODEL", "llama-3.3-70b-versatile"),
        )
    )
    return client.complete_json(
        system_prompt=system_prompt,
        user_prompt=json.dumps(payload, indent=2),
    )


def enrich_pulse(pulse: dict, quotes: list[dict], *, use_groq: bool) -> dict:
    quotes_by_theme: dict[str, list[str]] = defaultdict(list)
    for row in quotes:
        if isinstance(row, dict) and row.get("theme_name") and row.get("quote_text"):
            quotes_by_theme[str(row["theme_name"])].append(str(row["quote_text"]))

    groq_payload = _generate_with_groq(pulse, quotes_by_theme) if use_groq else None
    theme_bullets_map: dict[str, list[str]] = {}
    action_bullets_map: dict[str, list[str]] = {}

    if groq_payload:
        for theme in groq_payload.get("top_themes") or []:
            if isinstance(theme, dict) and theme.get("theme_name"):
                points = theme.get("bullet_points") or []
                if isinstance(points, list) and len(points) >= BULLET_COUNT:
                    theme_bullets_map[str(theme["theme_name"])] = [
                        str(point).strip() for point in points[:BULLET_COUNT]
                    ]
        for action in groq_payload.get("action_ideas") or []:
            if isinstance(action, dict) and action.get("linked_theme"):
                points = action.get("bullet_points") or []
                if isinstance(points, list) and len(points) >= BULLET_COUNT:
                    action_bullets_map[str(action["linked_theme"])] = [
                        str(point).strip() for point in points[:BULLET_COUNT]
                    ]
        print("Generated bullets via Groq.")

    enriched = dict(pulse)
    for theme in enriched.get("top_themes") or []:
        if not isinstance(theme, dict):
            continue
        name = str(theme.get("theme_name", ""))
        theme["bullet_points"] = theme_bullets_map.get(name) or _bullets_from_quotes(
            name,
            str(theme.get("summary", "")),
            quotes_by_theme.get(name, []),
        )

    for action in enriched.get("action_ideas") or []:
        if not isinstance(action, dict):
            continue
        linked = str(action.get("linked_theme", ""))
        action["bullet_points"] = action_bullets_map.get(linked) or _bullets_from_action(
            str(action.get("action", "")),
            linked,
        )

    return enriched


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--week", default="2026-05-21", help="Week-ending folder name")
    parser.add_argument("--no-groq", action="store_true", help="Skip Groq; use quote-based bullets")
    args = parser.parse_args()

    _load_dotenv()
    week_dir = REPO_ROOT / "data" / "history" / "weekly_pulse" / args.week
    pulse_path = week_dir / "weekly_pulse.json"
    quotes_path = week_dir / "quote_candidates.json"

    if not pulse_path.exists():
        raise SystemExit(f"Missing {pulse_path}")

    pulse = _load_json(pulse_path)
    if not isinstance(pulse, dict):
        raise SystemExit("weekly_pulse.json must be an object.")

    quotes: list[dict] = []
    if quotes_path.exists():
        raw_quotes = _load_json(quotes_path)
        if isinstance(raw_quotes, list):
            quotes = [row for row in raw_quotes if isinstance(row, dict)]

    enriched = enrich_pulse(pulse, quotes, use_groq=not args.no_groq)
    _write_json(pulse_path, enriched)

    phase2_copy = (
        REPO_ROOT / "phase-2" / "output" / "phase2-2026-05-21-a592cc6c" / "weekly_pulse.json"
    )
    if phase2_copy.parent.exists():
        _write_json(phase2_copy, enriched)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
