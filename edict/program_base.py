"""Base definitions for Edict program objects."""

from decimal import Decimal
from enum import Enum
from typing import Generic, Optional, TypeVar

from .types import Record

__all__ = ["DataType", "ERuntimeError", "Error", "ProgramElement", "T", "string_encode"]


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


class EPrepareError(Error):
    """Error when preparing an Edict program."""


class ERuntimeError(Error):
    """An Edict runtime error."""

    def __init__(self, *args, record: Optional[Record] = None):
        self.record = record

    def __str__(self) -> str:
        error_str = super().__str__()
        if self.record is not None:
            error_str = "\n".join(
                [
                    error_str,
                    "Error occurred while processing record:",
                    "\n".join(
                        f"\t{key}: {value}" for key, value in self.record.items()
                    ),
                ]
            )
        return error_str


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
            raise ERuntimeError(f"Error in {self!s}:\n{e!s}", record=record) from e

    def _call(self, record: Record) -> T:
        """Evaluate on the given record."""
        raise NotImplementedError


class _StringEncodeNumber(ProgramElement[str]):
    """Encode a number as a string."""

    def __init__(self, inner: ProgramElement[Decimal]):
        self.inner = inner

    def _call(self, record: Record) -> str:
        return str(self.inner(record))

    def __str__(self):
        return f"{self.__class__.__name__}({self.inner})"


class _StringEncodeBoolean(ProgramElement[str]):
    """Encode a Boolean as a string."""

    def __init__(self, inner: ProgramElement[bool]):
        self.inner = inner

    def _call(self, record: Record) -> str:
        return "true" if self.inner(record) else "false"

    def __str__(self):
        return f"{self.__class__.__name__}({self.inner})"


def string_encode(value: ProgramElement) -> ProgramElement[str]:
    """Encode the given value as a string."""
    if value.dtype in (DataType.STRING, DataType.INDEFINITE_STRING):
        return value
    if value.dtype == DataType.NUMBER:
        return _StringEncodeNumber(value)
    if value.dtype == DataType.BOOLEAN:
        return _StringEncodeBoolean(value)
    raise ValueError(f"No string encoding for value of type {value.dtype}")
