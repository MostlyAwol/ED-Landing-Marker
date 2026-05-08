from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class JournalReader:
    """Small helper to recover body radius from recent journal Scan events.

    Status.json often includes PlanetRadius while near a planet. This class is a
    fallback for cases where Status.json does not have it yet.
    """

    def __init__(self, journal_dir: str):
        self.journal_dir = Path(journal_dir).expanduser()
        self._last_radius_by_body: dict[str, float] = {}
        self._last_seen_file: Path | None = None
        self._last_size = 0

    def latest_journal(self) -> Path | None:
        files = sorted(self.journal_dir.glob("Journal.*.log"))
        return files[-1] if files else None

    def update(self) -> None:
        path = self.latest_journal()
        if not path:
            return

        if path != self._last_seen_file:
            self._last_seen_file = path
            self._last_size = 0

        try:
            size = path.stat().st_size
            if size < self._last_size:
                self._last_size = 0

            with path.open("r", encoding="utf-8-sig", errors="replace") as f:
                f.seek(self._last_size)
                for line in f:
                    self._handle_line(line)
                self._last_size = f.tell()
        except OSError:
            return

    def _handle_line(self, line: str) -> None:
        try:
            evt: dict[str, Any] = json.loads(line)
        except json.JSONDecodeError:
            return

        if evt.get("event") != "Scan":
            return

        radius = evt.get("Radius")
        body = evt.get("BodyName")
        if body and radius is not None:
            try:
                self._last_radius_by_body[str(body)] = float(radius)
            except (TypeError, ValueError):
                pass

    def radius_for_body(self, body_name: str | None) -> float | None:
        if not body_name:
            return None
        return self._last_radius_by_body.get(str(body_name))
