from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path

from ..config import get_user_config_dir


@dataclass
class _PrefsData:
    lead_time_minutes: int = 10
    week_start_day: int = 0  # 0 = Monday, 6 = Sunday


class PreferencesStore:
    """Thin wrapper around a JSON file in the XDG config dir."""

    def __init__(self) -> None:
        self._path: Path = get_user_config_dir() / "preferences.json"
        self._data = self._load()
        self._callbacks: list = []

    def on_changed(self, callback) -> None:
        self._callbacks.append(callback)

    def _notify(self) -> None:
        for cb in self._callbacks:
            cb()

    # ------------------------------------------------------------------ I/O

    def _load(self) -> _PrefsData:
        if self._path.exists():
            try:
                raw = json.loads(self._path.read_text())
                fields = _PrefsData.__dataclass_fields__
                return _PrefsData(**{k: v for k, v in raw.items() if k in fields})
            except Exception:
                pass
        return _PrefsData()

    def _save(self) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._path.write_text(json.dumps(asdict(self._data), indent=2))

    # ------------------------------------------------------------------ properties

    @property
    def lead_time_minutes(self) -> int:
        return self._data.lead_time_minutes

    @lead_time_minutes.setter
    def lead_time_minutes(self, value: int) -> None:
        self._data.lead_time_minutes = max(1, int(value))
        self._save()
        self._notify()

    @property
    def week_start_day(self) -> int:
        return self._data.week_start_day

    @week_start_day.setter
    def week_start_day(self, value: int) -> None:
        self._data.week_start_day = int(value)
        self._save()
        self._notify()
