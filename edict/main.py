"""Edict class"""
from __future__ import annotations

from typing import TYPE_CHECKING, TextIO, Union

from edict import parse
from edict.protocols import READERS, WRITERS
from edict.types import RecordStream

if TYPE_CHECKING:
    import os
    from edict.program import Program

__all__ = [
    "Edict",
    "load",
    "loads",
]


class Edict:
    """Transform dictionaries"""

    def __init__(self, program: Program):
        self._program = program

    def apply(
        self, in_: TextIO, out: TextIO, read_protocol="csv", write_protocol="csv"
    ) -> None:
        read = READERS[read_protocol]
        write = WRITERS[write_protocol]
        write(out, self.transform(read(in_)))
        pass

    def transform(self, data: RecordStream) -> RecordStream:
        """Transform a RecordStream

        Note that the individual records are modified in-place.
        """
        program = self._program
        fields = program.fields(data.fields)
        return RecordStream(
            fields=fields,
            records=(program.transform(record) for record in data.records),
        )


def loads(text: str) -> Edict:
    return Edict(parse.parse(text))


def load(file: Union[str, bytes, os.PathLike]) -> Edict:
    with open(file, "r") as f:
        return loads(f.read())
