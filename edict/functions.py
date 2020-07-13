"""Edict built-in functions

Classes are ProgramElement objects.
Functions create an implicit ProgramElement if necessary.
"""

from decimal import Decimal
from typing import Callable, Dict, Sequence

from .program_base import DataType, EPrepareError, ProgramElement, T
from .types import Record

__all__ = [
    "AsNumber",
    "AsString",
    "CaseFold",
    "FUNCTION_TABLE",
    "FunctionCall",
    "ReadDate",
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
    if value.dtype == dtype or value.dtype == DataType.INDEFINITE_STRING:
        return
    raise EPrepareError("Cannot interpret {value.dtype} as {dtype}")


def as_boolean(inner: ProgramElement) -> ProgramElement[bool]:
    if inner.dtype == DataType.BOOLEAN:
        return inner
    raise EPrepareError("Cannot interpret {value.dtype} as {dtype}")


class AsNumber(_ImplicitFunctionCall[Decimal]):
    """Interpret a value as a number."""

    name = "as_number"

    def __init__(
        self, inner: ProgramElement, *, separator: str = ",", implicit: bool = False
    ):
        dtype = DataType.NUMBER
        _check_interpret_type(inner, dtype)
        super().__init__(inner=inner, dtype=dtype, implicit=implicit)
        self.separator = separator

    def _call(self, record: Record) -> Decimal:
        value = self.inner(record)
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

    def _call(self, record: Record) -> str:
        return self.inner(record)


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

    def _call(self, record: Record) -> str:
        return self.inner(record).casefold()


def casefold(inner: ProgramElement[str]) -> ProgramElement[str]:
    return CaseFold(inner, implicit=True)


class ReadDate(FunctionCall[str]):
    """Read a date and format as an ISO 8601 string."""

    name = "read_date"

    def __init__(
        self, date_string: ProgramElement[str], date_format: ProgramElement[str]
    ):
        super().__init__(dtype=DataType.STRING)
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


# Public API functions
FUNCTION_TABLE: Dict[str, Callable[..., FunctionCall]] = {
    f.name: f for f in (AsNumber, ReadDate)  # type: ignore
}


def function_call(name: str, args: Sequence[ProgramElement]):
    try:
        f = FUNCTION_TABLE[name]
    except KeyError:
        raise EPrepareError(f"No function named {name!r}")
    return f(*args)
