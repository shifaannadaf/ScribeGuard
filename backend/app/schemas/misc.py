"""DEPRECATED — use app.schemas.pipeline / .submission instead.

This module is preserved as a thin shim to avoid breaking any in-flight imports.
"""
from app.schemas.pipeline import TranscribeResponse, GenerateSoapResponse as GenerateResponse  # noqa: F401
from app.schemas.submission import SubmitRequest as PushRequest, SubmitResponse as PushResponse  # noqa: F401
