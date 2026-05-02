"""
Audio-file storage helper used by the EncounterIntakeAgent.

Audio bytes are written to disk under ``settings.AUDIO_STORAGE_DIR`` (one
sub-folder per encounter). Database rows store only metadata + path so that
big binaries never bloat PostgreSQL.
"""
from __future__ import annotations

import os
from typing import Optional


class AudioStorage:
    def __init__(self, root: str):
        self.root = root
        os.makedirs(self.root, exist_ok=True)

    def encounter_dir(self, encounter_id: str) -> str:
        path = os.path.join(self.root, encounter_id)
        os.makedirs(path, exist_ok=True)
        return path

    def save(
        self,
        *,
        encounter_id: str,
        filename: str,
        content: bytes,
    ) -> str:
        safe = _sanitize_filename(filename) or "recording.webm"
        path = os.path.join(self.encounter_dir(encounter_id), safe)
        with open(path, "wb") as f:
            f.write(content)
        return path

    def read(self, path: str) -> Optional[bytes]:
        if not path or not os.path.isfile(path):
            return None
        with open(path, "rb") as f:
            return f.read()


def _sanitize_filename(name: str) -> str:
    return "".join(c for c in (name or "") if c.isalnum() or c in (".", "_", "-")).strip()
