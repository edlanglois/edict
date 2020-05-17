"""Classes representing an edict program."""
from __future__ import annotations

import re
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Optional, Sequence, Union

from edict.types import Record

__all__ = [
    "Assignment",
    "BinaryNumericOperator",
    "Conjunction",
    "DataType",
    "Disjunction",
    "Identifier",
    "Literal",
    "Match",
    "Program",
    "ProgramElement",
    "Record",
    "Rule",
    "UnaryMinus",
    "UnaryNot",
    "ValueComparisonOperator",
]


ValueType = Union[str, bool, Decimal, None]


class DataType(Enum):
    NONE = 0
    STRING = 1
    NUMBER = 2
    BOOLEAN = 3
    INDEFINITE_STRING = 4


class ProgramElement:
    """Interface of a program element."""

    def __init__(self, dtype: DataType):
        self.dtype = dtype

    def __call__(self, record: Record) -> ValueType:
        """Evaluate on the given record."""
        raise NotImplementedError


class Literal(ProgramElement):
    def __init__(self, value: Union[str, bool, Decimal], dtype: DataType):
        super().__init__(dtype=dtype)
        self.value = value

    def __call__(self, record: Record) -> Union[str, bool, Decimal]:
        return self.value

    def __str__(self):
        return str(self.value)


class Identifier(ProgramElement):
    def __init__(self, name: str):
        super().__init__(dtype=DataType.INDEFINITE_STRING)
        self.name = name

    def __call__(self, record: Record) -> str:
        return record.get(self.name, "")

    def __str__(self):
        return f"{{{self.name}}}"


class UnaryMinus(ProgramElement):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.NUMBER)
        _check_compatible(inner.dtype, self.dtype)
        self.inner = inner

    def __call__(self, record: Record) -> Decimal:
        inner_value = self.inner(record)
        inner_number = _astype(inner_value, self.inner.dtype, self.dtype)
        assert isinstance(inner_number, Decimal)
        return -inner_number

    def __str__(self):
        return f"-({self.inner})"


class _BinaryOperator(ProgramElement):
    def __init__(
        self,
        left: ProgramElement,
        right: ProgramElement,
        op: Callable[[Any, Any], Any],
        dtype: Union[DataType, Callable[[DataType, DataType], DataType]],
        dtype_in: Optional[DataType] = None,
    ):
        if isinstance(dtype, DataType) and dtype_in is None:
            dtype_in = dtype

        if dtype_in is not None:
            _check_compatible(left.dtype, dtype_in)
            _check_compatible(right.dtype, dtype_in)

        if not isinstance(dtype, DataType):
            # Rely on the dtype() function to do additional error checking
            dtype = dtype(left.dtype, right.dtype)

        super().__init__(dtype=dtype)
        self.left = left
        self.right = right
        self.op = op
        self.dtype_in = dtype_in

    def __call__(self, record: Record) -> ValueType:
        left_value = self.left(record)
        right_value = self.right(record)
        if self.dtype_in is not None:
            left_value = _astype(left_value, self.left.dtype, self.dtype_in)
            right_value = _astype(right_value, self.right.dtype, self.dtype_in)
        return self.op(left_value, right_value)

    def __str__(self):
        return f"{self.op}({self.left}, {self.right})"


class BinaryNumericOperator(_BinaryOperator):
    def __init__(
        self,
        left: ProgramElement,
        right: ProgramElement,
        op: Callable[[Decimal, Decimal], Decimal],
    ):
        super().__init__(left=left, right=right, op=op, dtype=DataType.NUMBER)


class ValueComparisonOperator(_BinaryOperator):
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
            left=left, right=right, op=op, dtype=DataType.BOOLEAN, dtype_in=dtype_in
        )


class Match(ProgramElement):
    def __init__(
        self,
        pattern: str,
        string: ProgramElement,
        is_regex: bool,
        case_insensitive: bool = False,
    ):
        super().__init__(dtype=DataType.BOOLEAN)
        self.pattern: Union[str, re.Pattern[str]] = pattern
        if is_regex:
            flags = re.IGNORECASE if case_insensitive else 0
            self.pattern = re.compile(self.pattern, flags)
        elif case_insensitive:
            self.pattern = self.pattern.lower()
        self.string = string
        _check_compatible(string.dtype, DataType.STRING)
        self.case_insensitive = case_insensitive

    def __call__(self, record: Record) -> bool:
        pattern = self.pattern
        string = self.string(record)
        assert isinstance(string, str)
        if isinstance(pattern, str):
            if self.case_insensitive:
                string = string.lower()
            return pattern in string
        else:
            return bool(pattern.search(string))

    def __str__(self):
        return f"{self.string}~{self.pattern}"


class UnaryNot(ProgramElement):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.BOOLEAN)
        _check_compatible(inner.dtype, self.dtype)
        self.inner = inner

    def __call__(self, record: Record) -> bool:
        inner_value = _astype(self.inner(record), self.inner.dtype, self.dtype)
        assert isinstance(inner_value, bool)
        return not inner_value

    def __str__(self):
        return "!({self.inner})"


class Conjunction(ProgramElement):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        for part in parts:
            _check_compatible(part.dtype, self.dtype)
        self.parts = parts

    def __call__(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return all(part(record) for part in self.parts)

    def __str__(self):
        return " & ".join(str(part) for part in self.parts)


class Disjunction(ProgramElement):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        for part in parts:
            _check_compatible(part.dtype, self.dtype)
        self.parts = parts

    def __call__(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return any(part(record) for part in self.parts)

    def __str__(self):
        return "\n".join(f"| {part}" for part in self.parts)


class Assignment(ProgramElement):
    def __init__(self, name: str, value: ProgramElement):
        super().__init__(dtype=DataType.NONE)
        self.name = name
        self.value = value

    def __call__(self, record: Record) -> None:
        value = self.value(record)
        value_str = _to_string(value)
        record[self.name] = value_str

    def __str__(self):
        return f"{self.name} {self.value}"


class Rule(ProgramElement):
    def __init__(self, condition: ProgramElement, assignments: Sequence[Assignment]):
        super().__init__(dtype=DataType.NONE)
        _check_compatible(condition.dtype, DataType.BOOLEAN)
        self.condition = condition
        self.assignments = assignments

    def __call__(self, record: Record) -> None:
        condition = _astype(
            self.condition(record), self.condition.dtype, DataType.BOOLEAN
        )
        assert isinstance(condition, bool)
        if condition:
            for assignment in self.assignments:
                assignment(record)

    def __str__(self):
        return f"if\n{self.condition}\nthen\n" + "".join(
            f"\t{a}\n" for a in self.assignments
        )


class Program(ProgramElement):
    def __init__(self, rules: Sequence[Rule]):
        self.rules = rules
        self.assigned_fields: Sequence[str] = tuple(
            set(
                [
                    assignment.name
                    for rule in self.rules
                    for assignment in rule.assignments
                ]
            )
        )

    def __call__(self, record: Record) -> None:
        for rule in self.rules:
            rule(record)

    def transform(self, record: Record) -> Record:
        """Return a transformed copy of a record."""
        new_record = record.copy()
        self(new_record)
        return new_record

    def __str__(self):
        return "\n".join(str(r) for r in self.rules)


def _astype(value: ValueType, dtype_in: DataType, dtype_out: DataType) -> ValueType:
    """Convert from one type to another using compatible casts.

    The only compatible casts are
    INDEFINITE_STRING => STRING
    INDEFINITE_STRING => NUMBER
    """
    if dtype_in == DataType.INDEFINITE_STRING:
        assert isinstance(value, str)
        if dtype_out == DataType.STRING:
            return value
        elif dtype_out == DataType.NUMBER:
            return Decimal(value)

    if dtype_in == dtype_out:
        return value

    raise ValueError(f"Expecting {dtype_out} but got {dtype_in}")


def _check_compatible(actual: DataType, expected: DataType) -> None:
    """Check type allowing for compatible casts.

    Raises a value error if `actual` is incompatible with `expected`.
    """
    if actual not in (expected, DataType.INDEFINITE_STRING) or (
        actual == DataType.INDEFINITE_STRING
        and expected not in (DataType.NUMBER, DataType.STRING)
    ):
        raise ValueError(f"Expected type {expected} but got {actual}")


def _to_string(value: ValueType) -> str:
    """Converte a value to string.

    Not restricted by compatible casting.
    """
    if isinstance(value, str):
        return value
    if isinstance(value, Decimal):
        return str(value)
    if value is True:
        return "true"
    if value is False:
        return "false"
    raise TypeError(f"No conversion from {value} to str")
