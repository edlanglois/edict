"""Stream editors."""
from .program_base import ProgramElement
from .types import RecordStream

__all__ = [
    "Reverse",
    "Sort",
    "STREAM_EDITORS",
    "StreamEditor",
]


class StreamEditor:
    name: str

    def __call__(self, data: RecordStream) -> RecordStream:
        raise NotImplementedError


class Reverse(StreamEditor):
    name = "reverse"

    def __init__(self):
        super().__init__()

    def __call__(self, data: RecordStream) -> RecordStream:
        return RecordStream(fields=data.fields, records=reversed(list(data.records)))


class Sort(StreamEditor):
    name = "sort"

    def __init__(self, key: ProgramElement):
        super().__init__()
        self.key = key

    def __call__(self, data: RecordStream) -> RecordStream:
        return RecordStream(
            fields=data.fields, records=sorted(data.records, key=self.key)
        )


STREAM_EDITORS = {e.name: e for e in [Reverse, Sort]}
