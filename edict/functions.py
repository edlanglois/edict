"""Edict built-in functions

Given that not all of these are currently exposed as public API functions, the
distinction between FunctionCall and other program elements is a bit fuzzy. The working
definition of a FunctionCall is something that could be exposed as a public API
function.

Classes are ProgramElement objects.
Functions create an implicit ProgramElement if necessary.
"""

import sys
from decimal import Decimal
from typing import Callable, Dict, Optional, Sequence, Type

from .program_base import (
    DataType,
    EPrepareError,
    ProgramElement,
    RuntimeContext,
    T,
    string_encode,
)
from .types import Record

__all__ = [
    "AsNumber",
    "AsString",
    "CaseFold",
    "FUNCTION_TABLE",
    "FunctionCall",
    "ReadDate",
    "SubString",
    "as_boolean",
    "as_number",
    "as_string",
    "as_type",
    "casefold",
    "function_call",
]


class FunctionCall(ProgramElement[T]):
    name: str


class _ImplicitFunctionCall(FunctionCall[T]):
    """A function call that may be implicit.

    An implicit function call does not appear in the source code.
    Implicit functions may only take a single argument.
    """

    def __init__(self, inner: ProgramElement, dtype: DataType, implicit: bool = False):
        super().__init__(dtype=dtype)
        self.inner = inner
        self.implicit = implicit

    def __str__(self):
        if self.implicit:
            return str(self.inner)
        else:
            return f"{self.name}({self.inner!s})"


def _check_interpret_type(value: ProgramElement, dtype: DataType) -> None:
    """Check that value can be interpreted as the given type.

    Raises:
        EPrepareError if `value` cannot be interpreted as `dtype`.
    """
    if value.dtype == dtype or value.dtype == DataType.INDETERMINANT_STRING:
        return
    raise EPrepareError(f"Cannot interpret {value.dtype} as {dtype}")


def as_boolean(inner: ProgramElement) -> ProgramElement[bool]:
    if inner.dtype == DataType.BOOLEAN:
        return inner
    raise EPrepareError(f"Cannot interpret {inner.dtype} as BOOLEAN")


class AsNumber(_ImplicitFunctionCall[Decimal]):
    """Interpret a value as a number."""

    name = "as_number"

    def __init__(
        self,
        inner: ProgramElement,
        *,
        separator: str = ",",
        implicit: bool = False,
    ):
        dtype = DataType.NUMBER
        _check_interpret_type(inner, dtype)
        super().__init__(inner=inner, dtype=dtype, implicit=implicit)
        self.separator = separator

    def _call(self, record: Record, context: RuntimeContext) -> Decimal:
        value = self.inner(record, context)
        if isinstance(value, Decimal):
            return value
        assert isinstance(
            value, str
        ), f"{self.__class__.__name__}: Invalid input {value!r}"
        return Decimal(value.replace(self.separator, ""))


def as_number(inner: ProgramElement) -> ProgramElement[Decimal]:
    if inner.dtype == DataType.NUMBER:
        return inner
    return AsNumber(inner, implicit=True)


class AsString(_ImplicitFunctionCall[str]):
    """Interpret a value a string."""

    name = "as_string"

    def __init__(self, inner: ProgramElement, *, implicit: bool = False):
        dtype = DataType.STRING
        _check_interpret_type(inner, dtype)
        super().__init__(inner=inner, dtype=dtype, implicit=implicit)

    def _call(self, record: Record, context: RuntimeContext) -> str:
        return self.inner(record, context)


def as_string(inner: ProgramElement) -> ProgramElement[str]:
    if inner.dtype == DataType.STRING:
        return inner
    return AsString(inner, implicit=True)


def as_type(inner: ProgramElement, dtype: DataType) -> ProgramElement:
    # Type inference for the dictionary is overly general
    return {  # type: ignore
        DataType.BOOLEAN: as_boolean,
        DataType.NUMBER: as_number,
        DataType.STRING: as_string,
    }[dtype](inner)


class CaseFold(_ImplicitFunctionCall[str]):
    """Casefold a string for case insensitive comparison."""

    name = "casefold"

    def __init__(self, inner: ProgramElement[str], implicit: bool = False):
        super().__init__(inner=inner, dtype=DataType.STRING, implicit=implicit)

    def _call(self, record: Record, context: RuntimeContext) -> str:
        return self.inner(record, context).casefold()


def casefold(inner: ProgramElement[str]) -> ProgramElement[str]:
    return CaseFold(inner, implicit=True)


class InputProtocol(FunctionCall[str]):
    """Name of the input protocol in the current runtime context."""

    name = "input_protocol"

    def __init__(self):
        super().__init__(dtype=DataType.STRING)

    def _call(self, record: Record, context: RuntimeContext) -> str:
        return context.input_protocol


class Log(FunctionCall[None]):
    """Log all arguments to standard error."""

    name = "log"

    def __init__(self, *args: ProgramElement):
        self.args = [string_encode(arg) for arg in args]

    def _call(self, record: Record, context: RuntimeContext) -> None:
        values = [arg(record, context) for arg in self.args]
        print(*values, file=sys.stderr)


class OutputProtocol(FunctionCall[str]):
    """Name of the output protocol in the current runtime context."""

    name = "output_protocol"

    def __init__(self):
        super().__init__(dtype=DataType.STRING)

    def _call(self, record: Record, context: RuntimeContext) -> str:
        return context.output_protocol


class ReadDate(FunctionCall[str]):
    """Read a date and format as an ISO 8601 string."""

    name = "read_date"

    def __init__(
        self, date_string: ProgramElement[str], date_format: ProgramElement[str]
    ):
        super().__init__(dtype=DataType.STRING)
        self.date_string = as_string(date_string)
        self.date_format = as_string(date_format)

    def _call(self, record: Record, context: RuntimeContext) -> str:
        import datetime

        return (
            datetime.datetime.strptime(
                self.date_string(record, context),
                self.date_format(record, context),
            )
            .date()
            .isoformat()
        )


class RecordStr(FunctionCall[str]):
    """Format the current record as a string.

    This is meant to be a pretty-printer, not an unambiguous serialization.
    """

    name = "record_str"

    def __init__(self, field_separator: str = "\n"):
        super().__init__(dtype=DataType.STRING)
        self.field_separator = field_separator

    def _call(self, record: Record, context: RuntimeContext) -> str:
        return self.field_separator.join(
            f"{key}: {value}" for key, value in record.items()
        )

    def __str__(self):
        return f"{self.name}()"


def _decimal_as_int(x: Decimal) -> int:
    """Interpret a decimal value as an integer if possible.

    Raises:
        ValueError if `x` is not an integer.
    """
    numerator, denominator = x.as_integer_ratio()
    if denominator != 1:
        raise ValueError(f"{x} is not an integer")
    assert numerator == x
    return numerator


class Replace(FunctionCall[str]):
    """Replace substrings in a string

    Args:
        inner: Perform replacement on this string.
        old: Substring to replace.
        new: Replace occurrences of `old` with `new`.
        count: Maximum number of occurrences to replace
    """

    name = "replace"

    def __init__(
        self,
        inner: ProgramElement[str],
        old: ProgramElement[str],
        new: ProgramElement[str],
        count: Optional[ProgramElement[Decimal]] = None,
    ) -> None:
        super().__init__(dtype=DataType.STRING)
        self.inner = as_string(inner)
        self.old = as_string(old)
        self.new = as_string(new)
        self.count = as_number(count) if count is not None else None

    def _call(self, record: Record, context: RuntimeContext) -> str:
        inner_value = self.inner(record, context)
        old_value = self.old(record, context)
        new_value = self.new(record, context)
        if self.count is not None:
            count_value = _decimal_as_int(self.count(record, context))
        else:
            count_value = -1
        return inner_value.replace(old_value, new_value, count_value)


class Round(FunctionCall[Decimal]):
    """Round number to a given number of decimal places

    Args:
        inner: Round this value
        ndigits: Optional integer number of decimal digits to round to.
                 Defaults to 0.
    """

    name = "round"

    def __init__(
        self,
        inner: ProgramElement[Decimal],
        ndigits: Optional[ProgramElement[Decimal]] = None,
    ):
        super().__init__(dtype=DataType.NUMBER)
        self.inner = as_number(inner)
        self.ndigits = as_number(ndigits) if ndigits is not None else None

    def _call(self, record: Record, context: RuntimeContext) -> Decimal:
        inner_value = self.inner(record, context)
        if self.ndigits is not None:
            ndigits_value = _decimal_as_int(self.ndigits(record, context))
        else:
            ndigits_value = 0
        return round(inner_value, ndigits_value)


class SubString(FunctionCall[str]):
    """Extract a substring.

    Args:
        inner: Take a substring of this string.
        start: Index of the start of the substring. The first character has index 0.
            Negative numbers count from the end. The last character has index -1.
        end: Index of one past the end of the substring.
    """

    name = "substring"

    def __init__(
        self,
        inner: ProgramElement[str],
        start: ProgramElement[Decimal],
        end: Optional[ProgramElement[Decimal]] = None,
    ):
        super().__init__(dtype=DataType.STRING)
        self.inner = as_string(inner)
        self.start = as_number(start)
        self.end = as_number(end) if end is not None else None

    def _call(self, record: Record, context: RuntimeContext) -> str:
        inner_value = self.inner(record, context)
        start_value = _decimal_as_int(self.start(record, context))
        if self.end is not None:
            end_value: Optional[int] = _decimal_as_int(self.end(record, context))
        else:
            end_value = None
        return inner_value[start_value:end_value]


# Public API functions
_PUBLIC_FUNCTIONS: Sequence[Type[FunctionCall]] = (
    AsNumber,
    InputProtocol,
    Log,
    OutputProtocol,
    ReadDate,
    RecordStr,
    Replace,
    Round,
    SubString,
)
FUNCTION_TABLE: Dict[str, Callable[..., FunctionCall]] = {
    f.name: f for f in _PUBLIC_FUNCTIONS
}


def function_call(name: str, args: Sequence[ProgramElement]):
    try:
        f = FUNCTION_TABLE[name]
    except KeyError:
        raise EPrepareError(f"No function named {name!r}") from None
    return f(*args)
