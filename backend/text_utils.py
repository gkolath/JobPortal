"""Text helpers for job descriptions and scraped content."""

from __future__ import annotations

import html
import re
from html.parser import HTMLParser


_WS_RE = re.compile(r"\s+")
# Fallback for broken / truncated markup
_TAG_RE = re.compile(r"<[^>]*>", re.IGNORECASE | re.DOTALL)


class _HTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self._parts: list[str] = []

    def handle_data(self, data: str) -> None:
        if data:
            self._parts.append(data)

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() in {"br", "p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in {"p", "div", "li", "tr", "h1", "h2", "h3", "h4"}:
            self._parts.append(" ")

    def get_text(self) -> str:
        return "".join(self._parts)


def html_to_text(value: str, max_len: int = 0) -> str:
    """Strip HTML tags/entities into plain readable text."""
    if not value:
        return ""

    text = value.replace("\xa0", " ")
    # Unescape repeatedly in case content was double-encoded (&lt;p&gt;...)
    for _ in range(3):
        unescaped = html.unescape(text)
        if unescaped == text:
            break
        text = unescaped

    try:
        extractor = _HTMLTextExtractor()
        extractor.feed(text)
        extractor.close()
        text = extractor.get_text()
    except Exception:
        text = _TAG_RE.sub(" ", text)

    # Safety pass for leftover / broken tags
    text = _TAG_RE.sub(" ", text)
    text = _WS_RE.sub(" ", text).strip()

    if max_len and len(text) > max_len:
        return text[: max_len - 1].rstrip() + "…"
    return text
