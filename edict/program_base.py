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


class EPrepareError(Error):
    """Error when preparing an Edict program."""


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
