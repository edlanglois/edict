"""IO Protocols"""

import functools
import importlib
from collections.abc import Callable
from typing import Any, TextIO

from ..types import RecordStream

__all__ = [
    "READERS",
    "WRITERS",
    "Reader",
    "Writer",
]

Reader = Callable[[TextIO], RecordStream]
Writer = Callable[[TextIO, RecordStream], None]


def _lazy_load(protocol: str, name: str) -> Callable[[dict], Any]:
    def load(args: dict):
        return functools.partial(
            getattr(importlib.import_module(f".{protocol}", __name__), name), args=args
        )

    return load


READERS: dict[str, Callable[[dict], Reader]] = {"csv": _lazy_load("csv", "read_csv")}
WRITERS: dict[str, Callable[[dict], Writer]] = {
    "csv": _lazy_load("csv", "write_csv"),
    "pattern": _lazy_load("pattern", "write_pattern"),
    "hledger": _lazy_load("hledger", "write_hledger_journal"),
    "beancount": _lazy_load("beancount", "write_beancount_journal"),
}
