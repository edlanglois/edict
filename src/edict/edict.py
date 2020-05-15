"""Edict class"""
from __future__ import annotations

from typing import TYPE_CHECKING, TextIO, Union

from edict.protocols import PROTOCOLS
from edict.transform import Transformer
from edict.types import Program, RecordStream

if TYPE_CHECKING:
    import os


class Edict:
    """Transform dictionaries"""

    def apply(self, in_: TextIO, out: TextIO, protocol="csv") -> None:
        read, write = PROTOCOLS[protocol]
        write(out, self.transform(read(in_)))
        pass

    def transform(self, data: RecordStream) -> RecordStream:
        """Transform a RecordStream

        Note that the individual records are modified in-place.
        """
        # Merge orignal and added keys, preseving order without duplicates
        fields = tuple(
            dict((x, None) for x in data.fields + self._program.assigned_fields).keys()
        )
        transformer = self._transformer
        return RecordStream(
            fields=fields,
            records=(transformer.transform(record) for record in data.records),
        )

    @staticmethod
    def load(file: Union[str, bytes, os.PathLike]):
        import edict.parse

        return Edict(edict.parse.parse_file(file))

    def __init__(self, program: Program):
        self._program = program
        self._transformer = Transformer(program)
