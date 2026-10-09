"""Data types used by the edict python package."""

from __future__ import annotations

from collections.abc import Iterable
from typing import NamedTuple

__all__ = [
    "Record",
    "RecordStream",
]

Record = dict[str, str]


class RecordStream(NamedTuple):
    fields: list[str]
    records: Iterable[Record]
