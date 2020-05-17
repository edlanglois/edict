"""Classes representing an edict program."""
from __future__ import annotations

from decimal import Decimal
from enum import Enum
from re import Pattern
from typing import Any, Dict, NamedTuple, Optional, Union

Record = Dict[str, str]


class DataType(Enum):
    STRING = 1
    NUMBER = 2
    BOOLEAN = 3
    FIELD_VALUE = 4


class Value(NamedTuple):
    """A data element in an edict program."""

    value: Union[str, bool, Decimal]
    dtype: DataType


class _ProgramElement:
    """Interface of a program element."""

    def __call__(self, record: Record) -> Any:
        """Evaluate on the given record."""
        raise NotImplementedError


class Literal(_ProgramElement):
    def __init__(self, value: Union[str, bool, Decimal], dtype: DataType):
        self.value = Value(value=value)
        self.dtype = dtype

    def __call__(self, record: Record) -> Value:
        return self.value


class Identifier(_ProgramElement):
    def __init__(self, name: str):
        self.name = name
        self.dtype = DataType.FIELD_STRING

    def __call__(self, record: Record) -> Value:
        return Value(value=record.get(self.name, ""), castable=True)

class UnaryMinus(_ProgramElement):
    def __init__(self, inner: _ProgramElement):
        self.inner = inner

    def __call__(self,


# class
