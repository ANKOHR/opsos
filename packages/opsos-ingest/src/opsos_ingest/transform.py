"""Dot-path mapping rules ported from webhookhub."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


class MissingField(KeyError):
    """Raised when a required mapping source path is absent."""


@dataclass(frozen=True)
class MappingRule:
    source: str
    target: str
    default: Any = None


def _read_path(payload: dict[str, Any], path: str) -> Any:
    current: Any = payload
    for part in path.split("."):
        if not isinstance(current, dict) or part not in current:
            raise MissingField(path)
        current = current[part]
    return current


def _write_path(output: dict[str, Any], path: str, value: Any) -> None:
    parts = path.split(".")
    if any(not part for part in parts):
        raise ValueError("dot paths must have non-empty segments")
    current = output
    for part in parts[:-1]:
        existing = current.get(part)
        if not isinstance(existing, dict):
            existing = {}
            current[part] = existing
        current = existing
    current[parts[-1]] = value


class Transform:
    def __init__(self, rules: list[MappingRule], constants: dict[str, Any] | None = None):
        self.rules = list(rules)
        self.constants = dict(constants or {})
        for rule in self.rules:
            if not rule.source or not rule.target:
                raise ValueError("mapping source and target paths must be non-empty")

    def apply(self, payload: dict[str, Any]) -> dict[str, Any]:
        output: dict[str, Any] = {}
        for rule in self.rules:
            try:
                value = _read_path(payload, rule.source)
            except MissingField:
                if rule.default is None:
                    raise
                value = rule.default
            _write_path(output, rule.target, value)
        output.update(self.constants)
        return output
