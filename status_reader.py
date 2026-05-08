from __future__ import annotations

import json
from pathlib import Path
from typing import Any


class StatusReader:
    def __init__(self, journal_dir: str):
        self.journal_dir = Path(journal_dir).expanduser()
        self.status_path = self.journal_dir / "Status.json"

    def read(self) -> dict[str, Any] | None:
        try:
            text = self.status_path.read_text(encoding="utf-8-sig")
            return json.loads(text)
        except FileNotFoundError:
            return None
        except json.JSONDecodeError:
            # Status.json can be read during the moment ED is replacing it.
            return None
        except OSError:
            return None

    @staticmethod
    def has_planet_position(status: dict[str, Any] | None) -> bool:
        if not status:
            return False
        return all(k in status for k in ("Latitude", "Longitude", "Heading"))

    @staticmethod
    def planet_radius(status: dict[str, Any] | None) -> float | None:
        if not status:
            return None
        value = status.get("PlanetRadius")
        try:
            return float(value) if value is not None else None
        except (TypeError, ValueError):
            return None
