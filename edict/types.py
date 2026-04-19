"""Data types used by the edict python package."""

from __future__ import annotations

from typing import Dict, Iterable, NamedTuple

__all__ = [
    "RecordStream",
    "Record",
]

Record = Dict[str, str]


class RecordStream(NamedTuple):
    fields: list[str]
    records: Iterable[Record]
