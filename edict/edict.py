"""Edict class"""
from __future__ import annotations

from typing import TYPE_CHECKING, TextIO, Union

from edict.protocols import READERS, WRITERS
from edict.types import RecordStream

if TYPE_CHECKING:
    import os
    from edict.program import Program


class Edict:
    """Transform dictionaries"""

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

    @staticmethod
    def load(file: Union[str, bytes, os.PathLike]):
        import edict.parse

        return Edict(edict.parse.parse_file(file))

    def __init__(self, program: Program):
        self._program = program
