"""Data types used by the edict python package."""
from __future__ import annotations

from typing import Dict, Iterable, NamedTuple, Tuple

__all__ = [
    "RecordStream",
    "Record",
]

Record = Dict[str, str]


class RecordStream(NamedTuple):
    fields: Tuple[str, ...]
    records: Iterable[Record]
