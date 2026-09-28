"""Thread-safe JSON Lines execution log ported from webhookhub."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from threading import RLock


@dataclass(frozen=True)
class LogEntry:
    event_id: str
    stage: str
    outcome: str
    detail: str
    timestamp: str


class ExecutionLog:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path is not None else None
        self.entries: list[LogEntry] = []
        self._lock = RLock()
        if self.path is not None:
            self.path.parent.mkdir(parents=True, exist_ok=True)

    def append(self, event_id: str, stage: str, outcome: str, detail: str = "") -> LogEntry:
        entry = LogEntry(
            event_id=str(event_id),
            stage=stage,
            outcome=outcome,
            detail=str(detail),
            timestamp=datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z"),
        )
        with self._lock:
            self.entries.append(entry)
            if self.path is not None:
                with self.path.open("a", encoding="utf-8", newline="\n") as output:
                    output.write(json.dumps(asdict(entry), sort_keys=True) + "\n")
        return entry

    def to_jsonl(self, path: str | Path) -> None:
        with self._lock, Path(path).open("w", encoding="utf-8", newline="\n") as output:
            output.writelines(
                json.dumps(asdict(entry), sort_keys=True) + "\n" for entry in self.entries
            )

    @classmethod
    def from_jsonl(cls, path: str | Path) -> ExecutionLog:
        log = cls()
        with Path(path).open("r", encoding="utf-8") as source:
            for line in source:
                if line.strip():
                    log.entries.append(LogEntry(**json.loads(line)))
        return log

    def summary(self) -> dict[tuple[str, str], int]:
        with self._lock:
            return dict(Counter((entry.stage, entry.outcome) for entry in self.entries))

    def entries_for(self, event_id: str) -> list[LogEntry]:
        with self._lock:
            return [entry for entry in self.entries if entry.event_id == str(event_id)]
