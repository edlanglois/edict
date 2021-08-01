"""Edict class"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, TextIO, Union

from edict import parse
from edict.program import Program, RuntimeContext
from edict.protocols import READERS, WRITERS
from edict.stream import StreamEditor
from edict.types import RecordStream

if TYPE_CHECKING:
    import os

__all__ = [
    "Edict",
    "load",
    "loads",
]


class Edict:
    """Transform dictionaries"""

    def __init__(self, program: Program, pre_transform: Optional[StreamEditor]):
        self._program = program
        self._pre_transform = pre_transform

    def apply(
        self, in_: TextIO, out: TextIO, read_protocol="csv", write_protocol="csv"
    ) -> None:
        read = READERS[read_protocol]()
        write = WRITERS[write_protocol]()
        context = RuntimeContext(
            input_protocol=read_protocol, output_protocol=write_protocol
        )
        write(out, self.transform(read(in_), context))
        pass

    def transform(self, data: RecordStream, context: RuntimeContext) -> RecordStream:
        """Transform a RecordStream

        Note that the individual records are modified in-place.
        """
        program = self._program
        if self._pre_transform:
            data = self._pre_transform(data)
        fields = program.fields(data.fields)
        return RecordStream(
            fields=fields,
            records=(program.transform(record, context) for record in data.records),
        )


def loads(text: str) -> Edict:
    program, pre_transform = parse.parse_text(text)
    return Edict(program, pre_transform)


def load(file: Union[str, bytes, os.PathLike]) -> Edict:
    program, pre_transform = parse.parse_file(file)
    return Edict(program, pre_transform)
