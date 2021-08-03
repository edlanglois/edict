"""IO Protocols"""
import functools
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


def _lazy_load(protocol: str, name: str) -> Callable[[Dict], Any]:
    def load(args: Dict):
        return functools.partial(
            getattr(importlib.import_module(f".{protocol}", __name__), name), args=args
        )

    return load


READERS: Dict[str, Callable[[Dict], Reader]] = {"csv": _lazy_load("csv", "read_csv")}
WRITERS: Dict[str, Callable[[Dict], Writer]] = {
    "csv": _lazy_load("csv", "write_csv"),
    "pattern": _lazy_load("pattern", "write_pattern"),
    "hledger": _lazy_load("hledger", "write_hledger_journal"),
}
