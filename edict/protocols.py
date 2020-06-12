"""IO Protocols"""
from __future__ import annotations

import os
from typing import Callable, Dict, TextIO

from edict.types import RecordStream

__all__ = [
    "READERS",
    "WRITERS",
    "read_csv",
    "write_csv",
]


def read_csv(f: TextIO) -> RecordStream:
    import csv

    reader = csv.DictReader(f)
    fields = reader.fieldnames
    if fields is None:
        raise ValueError("First line must contain field names.")

    return RecordStream(fields=list(fields), records=reader)


def write_csv(f: TextIO, data: RecordStream) -> None:
    import csv

    writer = csv.DictWriter(f, data.fields, lineterminator=os.linesep)
    writer.writeheader()
    writer.writerows(data.records)


_Reader = Callable[[TextIO], RecordStream]
_Writer = Callable[[TextIO, RecordStream], None]

READERS: Dict[str, _Reader] = {
    "csv": read_csv,
}
WRITERS: Dict[str, _Writer] = {
    "csv": write_csv,
}
