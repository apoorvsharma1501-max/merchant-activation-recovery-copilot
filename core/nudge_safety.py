"""Deterministic safety checks on every drafted merchant message.

Checks run on the message and on its English back-translation. They catch the
brief's critical errors (links, promises, invented numbers, compliance leaks,
R10 workarounds, wrong script). They do NOT prove the translation is good; a
person still has to review it.
"""
from __future__ import annotations

import re
import unicodedata

import config
from schemas.labels import RecommendedAction

_URL = re.compile(r"(https?://|www\.|\b[\w-]+\.(com|in|org|net|io|co)\b)", re.IGNORECASE)
_EMAIL = re.compile(r"\b\S+@\S+\.\w+\b")
_PHONE = re.compile(r"\+?\d[\d\s-]{8,}\d")
_CODE_LEAK = re.compile(r"\bR\d{2}\b")

PROMISE_PATTERNS = [
    r"\bguarantee", r"\bwill be (approved|activated|verified|live|accepted)\b", r"\bwithin\b",
    r"\b(today|tomorrow|tonight)\b", r"\b(day|days|hour|hours|week|weeks|month|months)\b",
    r"\bsoon\b", r"\bimmediately\b", r"\bassured?\b",
]
COMPLIANCE_LEAK_PATTERNS = [
    r"sanction", r"screening", r"watch ?list", r"blacklist", r"negative list", r"\baml\b",
    r"money laundering", r"terror", r"fraud", r"\bcompliance\b", r"\brisk\b",
]
WORKAROUND_PATTERNS = [
    r"different (business )?(category|type)", r"change (your|the) (business )?(category|type)",
    r"\bre-?apply", r"\breapply", r"another (business|account|entity|company|name)",
    r"new application", r"select (a|another|the correct)", r"\balternative", r"\binstead\b",
    r"\bappeal\b", r"\bresubmit",
]

# Content the brief never contains: reassurance, offers of help, implied support channels, marketing.
EXTRA_CONTENT_PATTERNS = [
    r"\bhere (if|for|to)\b", r"\bneed (any )?help\b", r"\bworr(y|ied|ies)\b", r"grow(ing)? your business",
    r"feel free", r"reach out", r"don'?t hesitate", r"happy to (help|assist)", r"contact us",
    r"support team", r"help ?desk",
]

_SCRIPT_RANGES = {
    "devanagari": (0x0900, 0x097F),
    "tamil": (0x0B80, 0x0BFF),
    "kannada": (0x0C80, 0x0CFF),
}


def _script_of(ch: str) -> str | None:
    cp = ord(ch)
    if cp < 0x0250:
        return "latin"
    for name, (lo, hi) in _SCRIPT_RANGES.items():
        if lo <= cp <= hi:
            return name
    return "other"


def script_share(text: str, script: str) -> float:
    letters = [c for c in text if c.isalpha() or unicodedata.category(c) in ("Mn", "Mc")]
    if not letters:
        return 0.0
    return sum(1 for c in letters if _script_of(c) == script) / len(letters)


def _numbers(text: str) -> set[int]:
    # \d matches Devanagari/Tamil/Kannada digits too; int() normalises them.
    return {int(m) for m in re.findall(r"\d+", text)}


def _hits(patterns: list[str], text: str, allowed_text: str) -> list[str]:
    """Words in `text` that match a pattern not already present in the approved brief.

    Returns the matched words themselves ("guaranteed", "days") so warnings read in plain language."""
    found = []
    for p in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m and not re.search(p, allowed_text, re.IGNORECASE):
            word = f'"{m.group(0).strip()}"'
            if word not in found:
                found.append(word)
    return found


def _list(items) -> str:
    return ", ".join(str(i) for i in items)


def check(message: str, back_translation: str, language: str, action: RecommendedAction,
          brief: str, step: str | None = None, sensitive: bool = False) -> list[str]:
    """Return a list of problems; empty means the draft passed every automatic check."""
    issues: list[str] = []
    if not message or not message.strip():
        return ["empty message"]
    both = f"{message}\n{back_translation}"

    if _URL.search(both) or _EMAIL.search(both):
        issues.append("contains a link or email address")
    if _PHONE.search(both):
        issues.append("contains a phone number")
    if _CODE_LEAK.search(both):
        issues.append("mentions an internal rejection code")
    extra_numbers = _numbers(both) - _numbers(brief)
    if extra_numbers:
        issues.append(f"contains numbers not in the approved wording: {_list(sorted(extra_numbers))}")
    if len(message) > config.NUDGE_MAX_CHARS:
        issues.append(f"too long ({len(message)} chars)")

    promises = _hits(PROMISE_PATTERNS, back_translation, brief)
    if promises:
        issues.append(f"possible promise or timeline: {_list(promises)}")
    extras = _hits(EXTRA_CONTENT_PATTERNS, back_translation, brief)
    if extras:
        issues.append(f"adds content not in the brief: {_list(extras)}")

    if action is RecommendedAction.COMPLIANCE_ROUTE or sensitive:
        leaks = _hits(COMPLIANCE_LEAK_PATTERNS, back_translation, "")
        if leaks:
            issues.append(f"possible compliance disclosure: {_list(leaks)}")
    if action is RecommendedAction.CLOSE_POLITELY:
        workarounds = _hits(WORKAROUND_PATTERNS, back_translation, "")
        if workarounds:
            issues.append(f"possible workaround suggested: {_list(workarounds)}")
    if action is RecommendedAction.REMINDER_NUDGE and step:
        tokens = [t for t in re.split(r"[^a-z]+", step.lower()) if len(t) >= 3]
        if tokens and not any(t in back_translation.lower() for t in tokens):
            issues.append(f"does not name the step '{step}'")

    script = config.LANGUAGE_SCRIPTS.get(language)
    if script:
        share = script_share(message, script)
        need = 0.95 if script == "latin" else 0.5
        if share < need:
            issues.append(f"not written in {script} script as expected for {language} ({share:.0%})")
    return issues
