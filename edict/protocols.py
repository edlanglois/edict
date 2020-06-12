"""IO Protocols"""
from __future__ import annotations

import io
import os
from typing import BinaryIO, Callable, Dict

from edict.types import RecordStream

__all__ = [
    "READERS",
    "WRITERS",
    "read_csv",
    "write_csv",
]


def read_csv(f: BinaryIO) -> RecordStream:
    import csv

    reader = csv.DictReader(io.TextIOWrapper(f, newline=""))
    fields = reader.fieldnames
    if fields is None:
        raise ValueError("First line must contain field names.")

    return RecordStream(fields=list(fields), records=reader)


def write_csv(f: BinaryIO, data: RecordStream) -> None:
    import csv

    writer = csv.DictWriter(
        io.TextIOWrapper(f, newline=""), data.fields, lineterminator=os.linesep
    )
    writer.writeheader()
    writer.writerows(data.records)


_Reader = Callable[[BinaryIO], RecordStream]
_Writer = Callable[[BinaryIO, RecordStream], None]

READERS: Dict[str, _Reader] = {
    "csv": read_csv,
}
WRITERS: Dict[str, _Writer] = {
    "csv": write_csv,
}
