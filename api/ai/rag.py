"""Small local documentation retriever for the Stage 06B assistant.

This deliberately uses a transparent lexical ranker and checked-in Markdown
sources, so it adds no external service or model dependency.
"""

import re
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DOC_SOURCES = (
    PROJECT_ROOT / "docs" / "ai_assistant.md",
    PROJECT_ROOT / "docs" / "data_dictionary.md",
)
STOP_WORDS = {
    "about", "after", "also", "and", "are", "can", "does", "for", "from",
    "how", "into", "its", "mean", "more", "the", "their", "this", "what",
    "when", "where", "which", "with", "would", "your",
}


def _terms(text: str) -> set[str]:
    return {term for term in re.findall(r"[a-z0-9_]+", text.casefold()) if len(term) > 2 and term not in STOP_WORDS}


def _sections(path: Path) -> list[dict[str, str]]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        return []
    sections: list[dict[str, str]] = []
    heading = path.stem.replace("_", " ").title()
    body: list[str] = []
    for line in content.splitlines():
        if line.startswith("#"):
            if body:
                sections.append({"source": path.name, "heading": heading, "text": "\n".join(body).strip()})
            heading = line.lstrip("# ").strip()
            body = []
        else:
            body.append(line)
    if body:
        sections.append({"source": path.name, "heading": heading, "text": "\n".join(body).strip()})
    return sections


def retrieve_documentation(question: str, limit: int = 3) -> list[dict[str, Any]]:
    """Return the best matching checked-in documentation sections."""
    query_terms = _terms(question)
    if not query_terms:
        return []
    ranked: list[tuple[float, dict[str, str]]] = []
    for path in DOC_SOURCES:
        for section in _sections(path):
            text_terms = _terms(section["heading"] + " " + section["text"])
            matched = query_terms & text_terms
            if not matched:
                continue
            # Prefer sections that cover more query terms, with a small boost for headings.
            heading_terms = _terms(section["heading"])
            score = len(matched) / len(query_terms) + 0.25 * len(matched & heading_terms)
            ranked.append((score, section))
    ranked.sort(key=lambda item: item[0], reverse=True)
    return [
        {"source": section["source"], "section": section["heading"], "excerpt": section["text"][:1800]}
        for score, section in ranked[:limit]
        if score > 0
    ]
