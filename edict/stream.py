"""Stream editors."""

from edict.types import RecordStream

__all__ = [
    "Reverse",
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

    def __call__(self, data):
        return RecordStream(fields=data.fields, records=reversed(list(data.records)))


STREAM_EDITORS = {e.name: e for e in [Reverse]}
