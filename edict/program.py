"""Classes representing an edict program."""
from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum
from typing import (
    Any,
    Callable,
    Dict,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Type,
    TypeVar,
)

from edict.types import Record
from edict.utils import OrderedSet

__all__ = [
    "Assignment",
    "BinaryOperator",
    "Conjunction",
    "DataType",
    "Disjunction",
    "Fields",
    "Identifier",
    "Literal",
    "Match",
    "Program",
    "ProgramElement",
    "Record",
    "Rule",
    "SubString",
    "UnaryMinus",
    "UnaryNot",
    "ValueComparisonOperator",
    "as_boolean",
    "as_number",
    "as_string",
    "as_type",
    "function_call",
    "string_encode",
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


# class ProgramContext(NamedTuple):
#     default_match_field: Optional[str] = None
#     case_insensitive: bool = False


T = TypeVar("T", str, bool, Decimal, None)
T1 = TypeVar("T1", str, bool, Decimal, None)
T2 = TypeVar("T2", str, bool, Decimal, None)


class ProgramElement(Generic[T]):
    """Interface of a program element."""

    def __init__(self, dtype: DataType):
        self.dtype = dtype

    def __call__(self, record: Record) -> T:
        """Evaluate on the given record."""
        raise NotImplementedError


T_literal = TypeVar("T_literal", str, bool, Decimal)


class Literal(ProgramElement[T_literal]):
    """Stores a constant value."""

    def __init__(self, value: T_literal, dtype: DataType):
        super().__init__(dtype=dtype)
        self.value: T_literal = value

    def __call__(self, record: Record) -> T_literal:
        return self.value

    def __str__(self):
        if isinstance(self.value, str):
            return repr(self.value)
        else:
            return str(self.value)


class Identifier(ProgramElement[str]):
    """Stores a record field name."""

    def __init__(self, name: str):
        super().__init__(dtype=DataType.INDEFINITE_STRING)
        self.name = name

    def __call__(self, record: Record) -> str:
        return record.get(self.name, "")

    def __str__(self):
        return f"{{{self.name}}}"


class _AsString(ProgramElement[str]):
    def __init__(self, inner: ProgramElement):
        dtype = DataType.STRING
        if inner.dtype != dtype and inner.dtype != DataType.INDEFINITE_STRING:
            raise ValueError(f"Expected {dtype} but got {inner.dtype}")
        super().__init__(dtype=dtype)
        self.inner: ProgramElement[str] = inner

    def __call__(self, record: Record) -> str:
        return self.inner(record)

    def __str__(self):
        return f"String({self.inner})"


def as_string(value: ProgramElement) -> ProgramElement[str]:
    if value.dtype == DataType.NUMBER:
        return value
    return _AsString(value)


class _AsNumber(ProgramElement[Decimal]):
    def __init__(self, inner: ProgramElement):
        dtype = DataType.NUMBER
        if inner.dtype != dtype and inner.dtype != DataType.INDEFINITE_STRING:
            raise ValueError(f"Expected {dtype} but got {inner.dtype}")
        super().__init__(dtype=dtype)
        self.inner = inner

    def __call__(self, record: Record) -> Decimal:
        value = self.inner(record)
        if isinstance(value, Decimal):
            return value
        assert isinstance(
            value, str
        ), f"{self.__class__.__name__}: Invalid input {value!r}"
        return Decimal(value)

    def __str__(self):
        return f"Number({self.inner})"


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


class _StringEncodeNumber(ProgramElement[str]):
    """Encode a number as a string."""

    def __init__(self, inner: ProgramElement[Decimal]):
        self.inner = inner

    def __call__(self, record: Record) -> str:
        return str(self.inner(record))

    def __str__(self):
        return f"{self.__class__.__name__}({self.inner})"


class _StringEncodeBoolean(ProgramElement[str]):
    """Encode a Boolean as a string."""

    def __init__(self, inner: ProgramElement[bool]):
        self.inner = inner

    def __call__(self, record: Record) -> str:
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


class _FunctionCall(ProgramElement[T]):
    name: str

    def __init__(self, args: Sequence[ProgramElement], dtype: DataType):
        super().__init__(dtype=dtype)
        self.args = args

    def __str__(self):
        arg_str = ",".join(str(arg) for arg in self.args)
        return f"{self.name}({arg_str})"


class _FReadDate(_FunctionCall[str]):
    """Read a date and format as an ISO 8601 string."""

    name = "read_date"

    def __init__(self, args: Sequence[ProgramElement]):
        super().__init__(args, dtype=DataType.STRING)
        date_string, date_format = args
        self.date_string = as_string(date_string)
        self.date_format = as_string(date_format)

    def __call__(self, record: Record) -> str:
        import datetime

        return (
            datetime.datetime.strptime(
                self.date_string(record), self.date_format(record)
            )
            .date()
            .isoformat()
        )


class _FNum(_FunctionCall[Decimal]):
    """Interpret a value as a number."""

    name = "num"

    def __init__(self, args: Sequence[ProgramElement]):
        super().__init__(args, dtype=DataType.NUMBER)
        (value,) = args
        self.value = as_number(value)

    def __call__(self, record: Record) -> Decimal:
        return self.value(record)


_FUNCTIONS: Dict[str, Callable[[Sequence[ProgramElement]], _FunctionCall]] = {
    f.name: f for f in (_FNum, _FReadDate)  # type: ignore
}


def function_call(name: str, args: Sequence[ProgramElement]):
    return _FUNCTIONS[name](args)


class UnaryMinus(ProgramElement[Decimal]):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.NUMBER)
        self.inner = as_number(inner)

    def __call__(self, record: Record) -> Decimal:
        return -self.inner(record)

    def __str__(self):
        return f"-({self.inner})"


class BinaryOperator(ProgramElement[T], Generic[T, T1, T2]):
    def __init__(
        self,
        left: ProgramElement,
        right: ProgramElement,
        op: Callable[[T1, T2], T],
        dtype: DataType,
        dtype_left: Optional[DataType] = None,
        dtype_right: Optional[DataType] = None,
    ):
        super().__init__(dtype=dtype)
        if dtype_left is None:
            dtype_left = dtype
        if dtype_right is None:
            dtype_right = dtype
        self.left: ProgramElement[T1] = as_type(left, dtype_left)
        self.right: ProgramElement[T2] = as_type(right, dtype_right)
        self.op: Callable[[T1, T2], T] = op

    def __call__(self, record: Record) -> T:
        left_value = self.left(record)
        right_value = self.right(record)
        return self.op(left_value, right_value)

    def __str__(self):
        return f"{self.left} .{self.op.__name__}. {self.right}"


class ValueComparisonOperator(BinaryOperator[bool, Any, Any]):
    """Compare two values."""

    def __init__(
        self,
        left: ProgramElement,
        right: ProgramElement,
        op: Callable[[Any, Any], bool],
    ):
        # Default to STRING if neither is concrete
        dtype_in = DataType.STRING
        if left.dtype != DataType.INDEFINITE_STRING:
            dtype_in = left.dtype
        elif right.dtype != DataType.INDEFINITE_STRING:
            dtype_in = right.dtype
        if dtype_in not in (DataType.STRING, DataType.NUMBER):
            raise ValueError("Comparison only defined for strings and numbers")
        super().__init__(
            left=left,
            right=right,
            op=op,
            dtype=DataType.BOOLEAN,
            dtype_left=dtype_in,
            dtype_right=dtype_in,
        )


class Match(ProgramElement[bool]):
    def __init__(
        self,
        pattern: Literal[str],
        string: ProgramElement,
        case_insensitive: bool = False,
    ):
        super().__init__(dtype=DataType.BOOLEAN)
        if pattern.dtype == DataType.REGEX:
            flags = re.IGNORECASE if case_insensitive else 0
            self.compiled_pattern = re.compile(pattern.value, flags)
        self.string = as_string(string)

    def __call__(self, record: Record) -> bool:
        string = self.string(record)
        return bool(self.compiled_pattern.search(string))

    def __str__(self):
        return f"{self.string} ~ {self.compiled_pattern}"


class SubString(ProgramElement[bool]):
    def __init__(
        self,
        substring: Literal[str],
        string: ProgramElement,
        case_insensitive: bool = False,
    ):
        super().__init__(dtype=DataType.BOOLEAN)
        self.substring = substring.value
        if case_insensitive:
            self.substring = self.substring.lower()
        self.string = as_string(string)
        self.case_insensitive = case_insensitive

    def __call__(self, record: Record) -> bool:
        string = self.string(record)
        if self.case_insensitive:
            string = string.lower()
        return self.substring in string

    def __str__(self):
        return f"{self.string} ~ {self.substring!r}"


class UnaryNot(ProgramElement[bool]):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.BOOLEAN)
        self.inner = as_boolean(inner)

    def __call__(self, record: Record) -> bool:
        return not self.inner(record)

    def __str__(self):
        return "!({self.inner})"


class Conjunction(ProgramElement[bool]):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        self.parts = [as_boolean(part) for part in parts]

    def __call__(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return all(part(record) for part in self.parts)

    def __str__(self):
        return " & ".join(str(part) for part in self.parts)


class Disjunction(ProgramElement[bool]):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        self.parts = [as_boolean(part) for part in parts]

    def __call__(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return any(part(record) for part in self.parts)

    def __str__(self):
        return "\n".join(f"| {part}" for part in self.parts)


class _Executable(ProgramElement[None]):
    """Execute some behaviour on a record."""

    def fields(self, input_fields: Iterable[str]) -> List[str]:
        fields = OrderedSet(input_fields)
        self._update_fields(fields)
        return list(fields)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        raise NotImplementedError


class Assignment(_Executable):
    """Assign a value to a field."""

    def __init__(self, name: str, value: ProgramElement):
        super().__init__(dtype=DataType.NONE)
        self.name = name
        self.value = string_encode(value)

    def __call__(self, record: Record) -> None:
        record[self.name] = self.value(record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        fields.add(self.name)

    def __str__(self):
        return f"{{{self.name}}} = {self.value}"


class Rule(_Executable):
    """Conditionally execute some statements"""

    def __init__(self, condition: ProgramElement, statements: Sequence[_Executable]):
        super().__init__(dtype=DataType.NONE)
        self.condition = as_boolean(condition)
        self.statements = statements

    def __call__(self, record: Record) -> None:
        if self.condition(record):
            for statements in self.statements:
                statements(record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        for statement in self.statements:
            statement._update_fields(fields)

    def __str__(self):
        return f"if\n{self.condition}\nthen\n" + "".join(
            f"\t{s}\n" for s in self.statements
        )


class Fields(_Executable):
    """Specify an explicit set of fields, dropping all others."""

    def __init__(self, fields: Iterable[str]):
        self._fields = OrderedSet(fields)

    def __call__(self, record: Record) -> None:
        new_record = {}
        for field in self._fields:
            try:
                new_record[field] = record[field]
            except KeyError:
                pass
        record.clear()
        record.update(new_record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        fields.clear()
        fields.update(self._fields)


class Program(_Executable):
    def __init__(self, statements: Sequence[_Executable]):
        self.statements = statements

    def __call__(self, record: Record) -> None:
        for statement in self.statements:
            statement(record)

    def transform(self, record: Record) -> Record:
        """Return a transformed copy of a record."""
        new_record = record.copy()
        self(new_record)
        return new_record

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        for statement in self.statements:
            statement._update_fields(fields)

    def __str__(self):
        return "\n".join(str(r) for r in self.rules)
