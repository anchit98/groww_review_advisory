"""Publication-time validation (structure, PII, word budget)."""

from __future__ import annotations

import re
from typing import Any

MAX_NOTE_WORDS = 250

# Lightweight PII guardrails for outbound channels (not a full DLP suite).
EMAIL_PATTERN = re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b")
PHONE_PATTERN = re.compile(r"\b(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{3}\)?[-.\s]?)?\d{3}[-.\s]?\d{4}\b")


class PublicationValidationError(ValueError):
    pass


def validate_weekly_pulse_shape(weekly_pulse: dict[str, Any]) -> None:
    required_top = ("opening_summary", "top_themes", "user_quotes", "action_ideas")
    for key in required_top:
        if key not in weekly_pulse:
            raise PublicationValidationError(f"Weekly pulse missing required field: {key}")
    if not isinstance(weekly_pulse["top_themes"], list) or not weekly_pulse["top_themes"]:
        raise PublicationValidationError("top_themes must be a non-empty list.")
    if not isinstance(weekly_pulse["user_quotes"], list) or not weekly_pulse["user_quotes"]:
        raise PublicationValidationError("user_quotes must be a non-empty list.")
    if not isinstance(weekly_pulse["action_ideas"], list) or not weekly_pulse["action_ideas"]:
        raise PublicationValidationError("action_ideas must be a non-empty list.")


def assert_no_obvious_pii(text: str) -> None:
    if EMAIL_PATTERN.search(text):
        raise PublicationValidationError("Rendered note contains an email-like pattern; refuse to publish.")
    if PHONE_PATTERN.search(text):
        raise PublicationValidationError("Rendered note contains a phone-like pattern; refuse to publish.")


def count_words(text: str) -> int:
    return len(re.findall(r"[A-Za-z0-9]+(?:'[A-Za-z0-9]+)?", text))


def substantive_word_count(weekly_pulse: dict[str, Any]) -> int:
    """Approximate word count for stakeholder-facing text (matches weekly pulse content, not boilerplate)."""
    chunks: list[str] = [str(weekly_pulse.get("opening_summary", ""))]
    for theme in weekly_pulse.get("top_themes") or []:
        chunks.append(str(theme.get("theme_name", "")))
        chunks.append(str(theme.get("summary", "")))
    for quote in weekly_pulse.get("user_quotes") or []:
        chunks.append(str(quote.get("quote", "")))
    for action in weekly_pulse.get("action_ideas") or []:
        chunks.append(str(action.get("action", "")))
        chunks.append(str(action.get("linked_theme", "")))
    if weekly_pulse.get("coverage_note"):
        chunks.append(str(weekly_pulse.get("coverage_note")))
    return count_words(" ".join(chunks))


def validate_substantive_word_budget(
    weekly_pulse: dict[str, Any],
    *,
    max_words: int = MAX_NOTE_WORDS,
) -> None:
    n = substantive_word_count(weekly_pulse)
    if n > max_words:
        raise PublicationValidationError(
            f"Weekly pulse substantive text is about {n} words; limit is {max_words}. "
            "Tighten Phase 2 output before publication."
        )
