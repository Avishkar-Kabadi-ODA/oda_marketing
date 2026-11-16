# Copyright (c) 2026, Optimum Data Analytics and contributors
# For license information, please see license.txt

"""Minimal, secret-safe logging for LLM calls. Never log prompts, responses, URLs, headers
or exception messages (they can contain drafts, keys or provider error bodies)."""

import logging

_logger = logging.getLogger("oda_marketing.ai")


def log_llm_event(stage, provider, model, docname, status, duration_ms=None, error=None):
    parts = [
        f"stage={stage}",
        f"provider={provider}",
        f"model={model}",
        f"doc={docname or 'N/A'}",
        f"status={status}",
    ]
    if duration_ms is not None:
        parts.append(f"duration_ms={int(duration_ms)}")
    if error is not None:
        parts.append(f"error_type={type(error).__name__}")
    _logger.info(" ".join(parts))