"""IO Protocols"""
import importlib
from typing import Any, Callable, Dict, TextIO

from ..types import RecordStream

__all__ = [
    "Reader",
    "Writer",
    "READERS",
    "WRITERS",
]

Reader = Callable[[TextIO], RecordStream]
Writer = Callable[[TextIO, RecordStream], None]


def _lazy_load(protocol: str, name: str) -> Callable[[], Any]:
    def load():
        return getattr(importlib.import_module(f".{protocol}", __name__), name)

    return load


READERS: Dict[str, Callable[[], Reader]] = {"csv": _lazy_load("csv", "read_csv")}
WRITERS: Dict[str, Callable[[], Writer]] = {
    "csv": _lazy_load("csv", "write_csv"),
    "hledger": _lazy_load("hledger", "write_hledger_journal"),
}
