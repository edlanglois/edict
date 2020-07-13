"""Edict built-in functions"""

from decimal import Decimal
from typing import Callable, Dict, Sequence

from .program_base import DataType, ProgramElement, T, as_number, as_string
from .types import Record

__all__ = ["CaseFold", "FunctionCall", "Num", "ReadDate", "function_call"]


class FunctionCall(ProgramElement[T]):
    name: str

    def __init__(self, args: Sequence[ProgramElement], dtype: DataType):
        super().__init__(dtype=dtype)
        self.args = args

    def __str__(self):
        arg_str = ",".join(str(arg) for arg in self.args)
        return f"{self.name}({arg_str})"


class CaseFold(FunctionCall[str]):
    """Casefold a string for case insensitive comparison."""

    name = "casefold"

    def __init__(self, args: Sequence[ProgramElement]):
        super().__init__(args, dtype=DataType.STRING)
        (self.arg,) = args

    def _call(self, record: Record) -> str:
        return self.arg(record).casefold()


class ReadDate(FunctionCall[str]):
    """Read a date and format as an ISO 8601 string."""

    name = "read_date"

    def __init__(self, args: Sequence[ProgramElement]):
        super().__init__(args, dtype=DataType.STRING)
        date_string, date_format = args
        self.date_string = as_string(date_string)
        self.date_format = as_string(date_format)

    def _call(self, record: Record) -> str:
        import datetime

        return (
            datetime.datetime.strptime(
                self.date_string(record), self.date_format(record)
            )
            .date()
            .isoformat()
        )


class Num(FunctionCall[Decimal]):
    """Interpret a value as a number."""

    name = "num"

    def __init__(self, args: Sequence[ProgramElement]):
        super().__init__(args, dtype=DataType.NUMBER)
        (value,) = args
        self.value = as_number(value)

    def _call(self, record: Record) -> Decimal:
        return self.value(record)


FUNCTION_TABLE: Dict[str, Callable[[Sequence[ProgramElement]], FunctionCall]] = {
    f.name: f for f in (CaseFold, Num, ReadDate)  # type: ignore
}


def function_call(name: str, args: Sequence[ProgramElement]):
    return FUNCTION_TABLE[name](args)
