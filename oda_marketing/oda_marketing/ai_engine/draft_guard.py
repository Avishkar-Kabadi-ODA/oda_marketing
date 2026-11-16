# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""Validates and bounds the draft text sent to the evaluator."""

MAX_DRAFT_CHARS = 60000


class DraftError(Exception):
    """The draft has no real text to evaluate."""


def _is_placeholder_line(line):
    line = line.strip()
    if not line:
        return True
    if line.startswith("===") and line.endswith("==="):
        return True
    return line.startswith("[") and line.endswith("]")


def has_real_text(text):
    return any(not _is_placeholder_line(line) for line in (text or "").splitlines())


def prepare_draft_text(text, max_chars=MAX_DRAFT_CHARS):
    """Return (text, truncated). Raise DraftError when only placeholders are present."""
    if not has_real_text(text):
        raise DraftError("No readable draft text was found in the notes or attachments.")
    text = text.strip()
    if len(text) > max_chars:
        return text[:max_chars], True
    return text, False