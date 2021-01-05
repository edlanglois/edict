"""CSV IO Protocol"""
from __future__ import annotations

import csv
from typing import Iterable, TextIO

from ..types import Record, RecordStream

__all__ = ["read_csv"]


def _csv_records(reader: csv.DictReader, file: TextIO) -> Iterable[Record]:
    for record in reader:
        if None in record:
            values = record[None]  # type: ignore
            raise ValueError(
                "\n".join(
                    [
                        "Error reading CSV input",
                        f"{file.name}:{reader.line_num}",
                        f"Encountered value(s) {values} not in a named CSV column.",
                    ]
                )
            )
        yield record


def read_csv(f: TextIO) -> RecordStream:
    reader = csv.DictReader(f)
    fields = reader.fieldnames
    if fields is None:
        raise ValueError("First line must contain field names.")

    return RecordStream(fields=list(fields), records=_csv_records(reader, f))


def write_csv(f: TextIO, data: RecordStream) -> None:
    writer = csv.DictWriter(f, data.fields, lineterminator="\n")
    writer.writeheader()
    writer.writerows(data.records)
