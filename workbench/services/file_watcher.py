"""stdlib 轮询文件监听:watch 目录里出现新 .md/.txt 就交给 file_route。

刻意不用 watchdog:零第三方依赖约束下轮询即可。去重状态落
``.processed.json``,重启不会重复处理同一个文件;文件内容变化
(mtime 变了)视为新版本,允许再次处理。
"""

from __future__ import annotations

import json
from pathlib import Path

_SUPPORTED = (".md", ".txt")
_STATE_FILE = ".processed.json"


class FileWatcher:
    def __init__(self, watch_dir: Path | str):
        self.watch_dir = Path(watch_dir)
        self.watch_dir.mkdir(parents=True, exist_ok=True)
        self._state_path = self.watch_dir / _STATE_FILE
        self._processed: dict[str, float] = self._load_state()

    def _load_state(self) -> dict[str, float]:
        try:
            raw = json.loads(self._state_path.read_text(encoding="utf-8"))
            return {name: float(mtime) for name, mtime in raw.items()}
        except (OSError, json.JSONDecodeError, ValueError):
            return {}

    def _save_state(self) -> None:
        self._state_path.write_text(
            json.dumps(self._processed, ensure_ascii=False, indent=1), encoding="utf-8"
        )

    def scan_once(self) -> list[Path]:
        """Return newly seen/changed files (marked processed immediately).

        Dedupe key is mtime **and** size: on Windows, two writes within the
        filesystem timestamp granularity can share an mtime, and a same-
        length edit would then be missed by mtime alone.
        """

        fresh: list[Path] = []
        for path in sorted(self.watch_dir.iterdir()):
            if not path.is_file() or path.suffix.lower() not in _SUPPORTED:
                continue
            stat = path.stat()
            fingerprint = f"{stat.st_mtime}:{stat.st_size}"
            if self._processed.get(path.name) == fingerprint:
                continue
            self._processed[path.name] = fingerprint
            fresh.append(path)
        if fresh:
            self._save_state()
        return fresh

    def forget(self, name: str) -> None:
        """Drop one file from the dedupe state (tests / re-delivery helper)."""

        if name in self._processed:
            del self._processed[name]
            self._save_state()
