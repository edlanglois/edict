"""IO Protocols"""
from __future__ import annotations

from typing import Callable, Dict, TextIO, Tuple

from edict.types import RecordStream

__all__ = [
    "read_csv",
    "write_csv",
    "PROTOCOLS",
]


def read_csv(f: TextIO) -> RecordStream:
    import csv

    reader = csv.DictReader(f)
    fields = reader.fieldnames
    if fields is None:
        raise ValueError("First line must contain field names.")

    return RecordStream(fields=tuple(fields), records=reader)


def write_csv(f: TextIO, data: RecordStream) -> None:
    import csv

    writer = csv.DictWriter(f, data.fields)
    writer.writeheader()
    writer.writerows(data.records)


_Reader = Callable[[TextIO], RecordStream]
_Writer = Callable[[TextIO, RecordStream], None]

PROTOCOLS: Dict[str, Tuple[_Reader, _Writer]] = {
    "csv": (read_csv, write_csv),
}
