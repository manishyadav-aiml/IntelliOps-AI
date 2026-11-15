"""Paragraph-aware chunking with overlap. Chunks never span pages, so page numbers stay accurate."""

import re
from dataclasses import dataclass

from app.rag.document_loader import PageText


@dataclass
class Chunk:
    chunk_id: str  # unique within a document, e.g. c0007
    index: int
    page_number: int | None
    text: str


def _split_long(text: str, size: int, overlap: int) -> list[str]:
    pieces, start = [], 0
    while start < len(text):
        end = min(start + size, len(text))
        if end < len(text):  # prefer to cut at whitespace
            cut = text.rfind(" ", start + size // 2, end)
            end = cut if cut > start else end
        pieces.append(text[start:end].strip())
        if end >= len(text):
            break
        start = max(end - overlap, start + 1)
    return [p for p in pieces if p]


def chunk_pages(pages: list[PageText], chunk_size: int = 800, overlap: int = 100) -> list[Chunk]:
    if chunk_size < 100:
        raise ValueError("chunk_size must be at least 100 characters")
    if not 0 <= overlap < chunk_size // 2:
        raise ValueError("overlap must be >= 0 and smaller than half of chunk_size")
    chunks: list[Chunk] = []
    for page in pages:
        paragraphs = [" ".join(p.split()) for p in re.split(r"\n\s*\n", page.text) if p.strip()]
        current = ""
        for paragraph in paragraphs:
            for piece in _split_long(paragraph, chunk_size, overlap) if len(paragraph) > chunk_size else [paragraph]:
                if current and len(current) + 1 + len(piece) > chunk_size:
                    chunks.append(Chunk(f"c{len(chunks):04d}", len(chunks), page.page_number, current))
                    tail = current[-overlap:].split(" ", 1)[-1] if overlap else ""
                    current = f"{tail} {piece}".strip() if overlap and tail else piece
                    if len(current) > chunk_size:
                        current = piece
                else:
                    current = f"{current}\n{piece}".strip() if current else piece
        if current:
            chunks.append(Chunk(f"c{len(chunks):04d}", len(chunks), page.page_number, current))
    return chunks
