"""Text helpers for job descriptions and scraped content."""

from __future__ import annotations

import html
import re


_TAG_RE = re.compile(r"<[^>]+>", re.IGNORECASE)
_WS_RE = re.compile(r"\s+")


def html_to_text(value: str, max_len: int = 0) -> str:
    """Strip HTML tags/entities into plain readable text."""
    if not value:
        return ""
    text = value
    # Preserve paragraph breaks before stripping tags
    text = re.sub(r"(?i)<\s*br\s*/?\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*p\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*li\s*>", "\n", text)
    text = re.sub(r"(?i)</\s*h[1-6]\s*>", "\n", text)
    text = _TAG_RE.sub(" ", text)
    text = html.unescape(text)
    text = text.replace("\xa0", " ")
    text = _WS_RE.sub(" ", text).strip()
    if max_len and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text
