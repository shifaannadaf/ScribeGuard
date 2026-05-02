"""
Best-effort text extraction from arbitrary uploaded files.

Used by the transcript import endpoint. The goal is "any text-bearing file
should produce a usable transcript". Supports:

- plain text (any sensible encoding)
- subtitle files (.srt, .vtt) — timestamps stripped
- JSON (extracts obvious "text" / "transcript" fields, else stringifies)
- HTML / Markdown — naive tag strip
- PDF — via `pypdf` if installed
- DOCX — via `python-docx` if installed

Audio files are handled by the existing intake/transcription flow; this
module deals only with already-text content.
"""
from __future__ import annotations

import json
import logging
import re
from io import BytesIO
from pathlib import Path
from typing import Optional


logger = logging.getLogger("scribeguard.text_extract")


AUDIO_EXTS = {".webm", ".wav", ".mp3", ".m4a", ".mp4", ".ogg", ".oga", ".flac", ".aac"}
AUDIO_MIME_PREFIX = "audio/"


def is_audio(filename: Optional[str], content_type: Optional[str]) -> bool:
    """Return True if the file looks like audio (route to intake flow)."""
    if content_type and content_type.startswith(AUDIO_MIME_PREFIX):
        return True
    if filename:
        ext = Path(filename).suffix.lower()
        if ext in AUDIO_EXTS:
            return True
    return False


def extract_text(
    *,
    filename: Optional[str],
    content_type: Optional[str],
    data: bytes,
) -> str:
    """Best-effort text extraction. Raises ValueError with a clear message
    when a known format can't be handled (missing dependency, etc.)."""
    if not data:
        return ""

    ext = (Path(filename).suffix.lower() if filename else "")
    ct = (content_type or "").lower()

    # ── PDF ────────────────────────────────────────────────────────────
    if ext == ".pdf" or "pdf" in ct or data[:4] == b"%PDF":
        return _extract_pdf(data)

    # ── DOCX (real docx is a zip with word/document.xml) ──────────────
    if ext == ".docx" or "wordprocessingml" in ct or _looks_like_docx(data):
        return _extract_docx(data)

    # ── Subtitles ─────────────────────────────────────────────────────
    if ext == ".srt":
        return _strip_srt(_decode_text(data))
    if ext == ".vtt":
        return _strip_vtt(_decode_text(data))

    # ── JSON ──────────────────────────────────────────────────────────
    if ext == ".json" or ct == "application/json":
        text = _decode_text(data)
        try:
            obj = json.loads(text)
        except json.JSONDecodeError:
            return text  # fall back to raw text
        return _flatten_json_text(obj) or text

    # ── HTML / Markdown ───────────────────────────────────────────────
    if ext in (".html", ".htm") or "html" in ct:
        return _strip_html(_decode_text(data))

    # ── Default: decode as text ───────────────────────────────────────
    return _decode_text(data)


# ── Internals ───────────────────────────────────────────────────────────

def _decode_text(data: bytes) -> str:
    for enc in ("utf-8", "utf-16", "latin-1"):
        try:
            return data.decode(enc)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _strip_srt(text: str) -> str:
    """Strip SRT index lines and `00:00:00,000 --> 00:00:00,000` cues."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.isdigit():
            continue
        if "-->" in s:
            continue
        out.append(s)
    return " ".join(out)


def _strip_vtt(text: str) -> str:
    """Same idea for WebVTT — drop WEBVTT header, NOTE blocks, and timing cues."""
    out: list[str] = []
    for line in text.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.upper().startswith("WEBVTT"):
            continue
        if s.upper().startswith("NOTE"):
            continue
        if "-->" in s:
            continue
        # Cue identifiers (numeric or arbitrary names) — best-effort skip
        if re.match(r"^[\w\-]+$", s) and any(c.isdigit() for c in s) and len(s) <= 16:
            continue
        out.append(s)
    return " ".join(out)


_HTML_TAG_RE = re.compile(r"<[^>]+>")
_HTML_WS_RE = re.compile(r"\s+")


def _strip_html(text: str) -> str:
    no_tags = _HTML_TAG_RE.sub(" ", text)
    return _HTML_WS_RE.sub(" ", no_tags).strip()


def _flatten_json_text(obj: object) -> str:
    """Pull out plausible transcript fields from common JSON shapes."""
    KEYS = ("transcript", "text", "content", "raw_text", "formatted_text")
    if isinstance(obj, dict):
        for k in KEYS:
            v = obj.get(k)
            if isinstance(v, str) and v.strip():
                return v
        # Common Whisper-verbose shape: {"segments": [{"text": "..."}, ...]}
        segs = obj.get("segments")
        if isinstance(segs, list):
            parts = [s.get("text", "") for s in segs if isinstance(s, dict)]
            joined = " ".join(p for p in parts if p).strip()
            if joined:
                return joined
    if isinstance(obj, list):
        parts = [_flatten_json_text(o) for o in obj]
        joined = " ".join(p for p in parts if p).strip()
        if joined:
            return joined
    return ""


def _looks_like_docx(data: bytes) -> bool:
    # DOCX is a ZIP (PK) — we still need the lib to actually parse it. This
    # heuristic just lets us route through the docx branch for the error msg.
    return data[:2] == b"PK"


def _extract_pdf(data: bytes) -> str:
    try:
        from pypdf import PdfReader  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "PDF imports require the `pypdf` package. "
            "Install it with: pip install pypdf"
        ) from exc
    reader = PdfReader(BytesIO(data))
    pages = [(p.extract_text() or "") for p in reader.pages]
    text = "\n".join(pages).strip()
    if not text:
        raise ValueError(
            "Could not extract text from this PDF — it may be a scanned image. "
            "OCR is not supported here."
        )
    return text


def _extract_docx(data: bytes) -> str:
    try:
        from docx import Document  # type: ignore
    except ImportError as exc:
        raise ValueError(
            "DOCX imports require the `python-docx` package. "
            "Install it with: pip install python-docx"
        ) from exc
    doc = Document(BytesIO(data))
    parts = [p.text for p in doc.paragraphs if p.text]
    return "\n".join(parts).strip()
