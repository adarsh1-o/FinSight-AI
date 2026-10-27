"""Load and chunk only the Markdown documents approved for assistant retrieval."""

from __future__ import annotations

import hashlib
import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOCUMENTS = (
    PROJECT_ROOT / "docs" / "ai_assistant.md",
    PROJECT_ROOT / "docs" / "data_dictionary.md",
)
DEFAULT_CHUNK_SIZE = 1200  # characters, including heading context
DEFAULT_CHUNK_OVERLAP = 150  # characters repeated between adjacent chunks


def chunking_settings() -> tuple[int, int]:
    size = int(os.getenv("FINSIGHT_RAG_CHUNK_SIZE", DEFAULT_CHUNK_SIZE))
    overlap = int(os.getenv("FINSIGHT_RAG_CHUNK_OVERLAP", DEFAULT_CHUNK_OVERLAP))
    if size < 100:
        raise ValueError("FINSIGHT_RAG_CHUNK_SIZE must be at least 100 characters.")
    if overlap < 0 or overlap >= size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size.")
    return size, overlap


@dataclass(frozen=True)
class MarkdownDocument:
    path: str
    text: str


@dataclass(frozen=True)
class DocumentChunk:
    chunk_id: str
    document_id: str
    source: str
    section: str
    chunk_index: int
    text: str

    def as_dict(self) -> dict[str, str | int]:
        return {
            "chunk_id": self.chunk_id,
            "document_id": self.document_id,
            "source": self.source,
            "section": self.section,
            "chunk_index": self.chunk_index,
            "text": self.text,
        }


def load_markdown_documents(paths: tuple[Path, ...] | list[Path] | None = None) -> list[MarkdownDocument]:
    """Read the configured Markdown files; ignore missing and empty documents."""
    documents = []
    for path in DEFAULT_DOCUMENTS if paths is None else paths:
        try:
            content = path.read_text(encoding="utf-8").strip()
        except OSError:
            continue
        if not content:
            continue
        try:
            source = path.resolve().relative_to(PROJECT_ROOT.resolve()).as_posix()
        except ValueError:
            source = path.name
        documents.append(MarkdownDocument(path=source, text=content))
    return documents


def _content_blocks(section_text: str) -> list[str]:
    """Split at blank lines while keeping fenced code blocks intact."""
    blocks: list[str] = []
    current: list[str] = []
    in_fence = False
    for line in section_text.splitlines():
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
        if not line.strip() and not in_fence:
            if current:
                blocks.append("\n".join(current).strip())
                current = []
            continue
        current.append(line)
    if current:
        blocks.append("\n".join(current).strip())
    return [block for block in blocks if block]


def _split_long_block(text: str, size: int, overlap: int) -> list[str]:
    if len(text) <= size:
        return [text]
    pieces = []
    start = 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):
            split_at = text.rfind(" ", start + int(size * 0.7), end)
            if split_at > start:
                end = split_at
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(start + 1, end - overlap)
    return pieces


def _section_blocks(markdown: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading_stack: list[str] = []
    current_lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("#"):
            if current_lines:
                sections.append((" > ".join(heading_stack) or "Introduction", "\n".join(current_lines).strip()))
                current_lines = []
            level = len(line) - len(line.lstrip("#"))
            title = line[level:].strip()
            heading_stack = heading_stack[: level - 1]
            heading_stack.append(title)
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((" > ".join(heading_stack) or "Introduction", "\n".join(current_lines).strip()))
    return sections


def chunk_documents(
    documents: list[MarkdownDocument],
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[DocumentChunk]:
    """Chunk sections into stable records; size and overlap are measured in characters."""
    configured_size, configured_overlap = chunking_settings()
    size = chunk_size if chunk_size is not None else configured_size
    overlap = chunk_overlap if chunk_overlap is not None else configured_overlap
    if size < 100:
        raise ValueError("FINSIGHT_RAG_CHUNK_SIZE must be at least 100 characters.")
    if overlap < 0 or overlap >= size:
        raise ValueError("Chunk overlap must be non-negative and smaller than chunk size.")

    chunks: list[DocumentChunk] = []
    for document in documents:
        document_id = hashlib.sha256(f"{document.path}\0{document.text}".encode("utf-8")).hexdigest()
        document_chunk_index = 0
        for section, section_text in _section_blocks(document.text):
            prefix = f"Section: {section}\n"
            content_limit = max(1, size - len(prefix))
            section_chunks: list[str] = []
            current = ""
            for block in _content_blocks(section_text):
                for piece in _split_long_block(block, content_limit, min(overlap, content_limit - 1)):
                    candidate = f"{current}\n\n{piece}".strip() if current else piece
                    if len(candidate) <= content_limit:
                        current = candidate
                    else:
                        if current:
                            section_chunks.append(current)
                        current = piece
            if current:
                section_chunks.append(current)

            for content in section_chunks:
                full_text = f"{prefix}{content}"[:size]
                chunk_id = hashlib.sha256(
                    f"{document.path}\0{section}\0{document_chunk_index}\0{full_text}".encode("utf-8")
                ).hexdigest()
                chunks.append(DocumentChunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    source=document.path,
                    section=section,
                    chunk_index=document_chunk_index,
                    text=full_text,
                ))
                document_chunk_index += 1
    return chunks
