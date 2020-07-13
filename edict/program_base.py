"""Base definitions for Edict program objects."""

from decimal import Decimal
from enum import Enum
from typing import Generic, TypeVar

from .types import Record

__all__ = [
    "DataType",
    "Error",
    "ERuntimeError",
    "ProgramElement",
    "T",
    "as_boolean",
    "as_number",
    "as_string",
    "as_type",
]


class DataType(Enum):
    """Runtime data types in an Edict program.

    Attributes:
       NONE: The type of expressions that have no value.
       STRING: A string.
       NUMBER: A decimal number.
       BOOLEAN: A boolean value.
       INDEFINITE_STRING: A string that can be cast to other types.
           Record values have this type.
       REGEX: A regular expression.
    """

    NONE = 0
    STRING = 1
    NUMBER = 2
    BOOLEAN = 3
    INDEFINITE_STRING = 4
    REGEX = 5

    def __str__(self):
        return self.name


# Possible value types for a program element
T = TypeVar("T", str, bool, Decimal, None)


class Error(Exception):
    pass


class ERuntimeError(Error):
    """An Edict runtime error."""


class ProgramElement(Generic[T]):
    """Interface of a program element."""

    def __init__(self, dtype: DataType):
        self.dtype = dtype

    def __call__(self, record: Record) -> T:
        """Evaluate on the given record."""
        try:
            return self._call(record)
        except ERuntimeError:
            raise
        except Exception as e:
            raise ERuntimeError(f"Error in {self!s}:\n{e!s}") from e

    def _call(self, record: Record) -> T:
        """Evaluate on the given record."""
        raise NotImplementedError


class _AsString(ProgramElement[str]):
    def __init__(self, inner: ProgramElement):
        dtype = DataType.STRING
        if inner.dtype != dtype and inner.dtype != DataType.INDEFINITE_STRING:
            raise ValueError(f"Expected {dtype} but got {inner.dtype}")
        super().__init__(dtype=dtype)
        self.inner: ProgramElement[str] = inner

    def _call(self, record: Record) -> str:
        return self.inner(record)

    def __str__(self):
        return f"String({self.inner})"


def as_string(value: ProgramElement) -> ProgramElement[str]:
    if value.dtype == DataType.NUMBER:
        return value
    return _AsString(value)


class _AsNumber(ProgramElement[Decimal]):
    def __init__(self, inner: ProgramElement, separator: str = ","):
        """Initialze an _AsNumber cast.

        Args:
            inner: The data to cast. Must have type NUMBER or INDEFINITE_STRING
            separator: The digits separator character.
        """
        dtype = DataType.NUMBER
        if inner.dtype != dtype and inner.dtype != DataType.INDEFINITE_STRING:
            raise ValueError(f"Expected {dtype} but got {inner.dtype}")
        super().__init__(dtype=dtype)
        self.inner = inner
        self.separator = separator

    def _call(self, record: Record) -> Decimal:
        value = self.inner(record)
        if isinstance(value, Decimal):
            return value
        assert isinstance(
            value, str
        ), f"{self.__class__.__name__}: Invalid input {value!r}"
        return Decimal(value.replace(self.separator, ""))

    def __str__(self):
        return f"Number({self.inner}, {self.separator!r})"


def as_number(value: ProgramElement) -> ProgramElement[Decimal]:
    if value.dtype == DataType.NUMBER:
        return value
    return _AsNumber(value)


def as_boolean(value: ProgramElement) -> ProgramElement[bool]:
    if value.dtype == DataType.BOOLEAN:
        return value
    raise ValueError(f"Expected BOOLEAN but got {value.dtype}")


def as_type(value: ProgramElement, dtype: DataType) -> ProgramElement:
    if dtype == value.dtype:
        return value
    if dtype == DataType.STRING:
        return as_string(value)
    if dtype == DataType.NUMBER:
        return as_number(value)
    if dtype == DataType.BOOLEAN:
        return as_boolean(value)
    raise ValueError(f"Expecting type {dtype} but got {value.dtype}")
