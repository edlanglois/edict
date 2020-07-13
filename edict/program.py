"""Classes representing the mapping parts of an edict program."""
from __future__ import annotations

import re
from decimal import Decimal
from typing import (
    Any,
    Callable,
    Generic,
    Iterable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
)

from .functions import (
    as_boolean,
    as_number,
    as_string,
    as_type,
    casefold,
    function_call,
)
from .program_base import DataType, ProgramElement, T, string_encode
from .types import Record
from .utils import OrderedSet

__all__ = [
    "Assignment",
    "BinaryOperator",
    "Conjunction",
    "DataType",
    "Disjunction",
    "Fields",
    "function_call",
    "Identifier",
    "Literal",
    "Match",
    "Program",
    "ProgramElement",
    "Record",
    "Rule",
    "Statements",
    "SubString",
    "UnaryMinus",
    "UnaryNot",
    "ValueComparisonOperator",
]


T_literal = TypeVar("T_literal", str, bool, Decimal)


class Literal(ProgramElement[T_literal]):
    """Stores a constant value."""

    def __init__(self, value: T_literal, dtype: DataType):
        super().__init__(dtype=dtype)
        self.value: T_literal = value

    def _call(self, record: Record) -> T_literal:
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

    def _call(self, record: Record) -> str:
        return record.get(self.name, "")

    def __str__(self):
        return f"{{{self.name}}}"


class UnaryMinus(ProgramElement[Decimal]):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.NUMBER)
        self.inner = as_number(inner)

    def _call(self, record: Record) -> Decimal:
        return -self.inner(record)

    def __str__(self):
        return f"-({self.inner})"


T1 = TypeVar("T1", str, bool, Decimal, None)
T2 = TypeVar("T2", str, bool, Decimal, None)


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

    def _call(self, record: Record) -> T:
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
        case_insensitive: bool = False,
    ):
        # Default to STRING if neither is concrete
        dtype_in = DataType.STRING
        if left.dtype != DataType.INDEFINITE_STRING:
            dtype_in = left.dtype
        elif right.dtype != DataType.INDEFINITE_STRING:
            dtype_in = right.dtype
        if dtype_in not in (DataType.STRING, DataType.NUMBER):
            raise ValueError("Comparison only defined for strings and numbers")
        if case_insensitive and dtype_in == DataType.STRING:
            left = casefold(left)
            right = casefold(right)
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

    def _call(self, record: Record) -> bool:
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
        self.string = as_string(string)
        if case_insensitive:
            self.substring = self.substring.casefold()
            self.string = casefold(self.string)

    def _call(self, record: Record) -> bool:
        string = self.string(record)
        return self.substring in string

    def __str__(self):
        return f"{self.string} ~ {self.substring!r}"


class UnaryNot(ProgramElement[bool]):
    def __init__(self, inner: ProgramElement):
        super().__init__(dtype=DataType.BOOLEAN)
        self.inner = as_boolean(inner)

    def _call(self, record: Record) -> bool:
        return not self.inner(record)

    def __str__(self):
        return "!({self.inner})"


class Conjunction(ProgramElement[bool]):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        self.parts = [as_boolean(part) for part in parts]

    def _call(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return all(part(record) for part in self.parts)

    def __str__(self):
        return " & ".join(str(part) for part in self.parts)


class Disjunction(ProgramElement[bool]):
    def __init__(self, parts: Sequence[ProgramElement]):
        super().__init__(dtype=DataType.BOOLEAN)
        self.parts = [as_boolean(part) for part in parts]

    def _call(self, record: Record) -> bool:
        # Short-circuiting evaluation
        return any(part(record) for part in self.parts)

    def __str__(self):
        return "\n".join(f"| {part}" for part in self.parts)


class _Executable(ProgramElement[None]):
    """Execute some behaviour on a record."""

    def __init__(self):
        super().__init__(dtype=DataType.NONE)

    def fields(self, input_fields: Iterable[str]) -> List[str]:
        fields = OrderedSet(input_fields)
        self._update_fields(fields)
        return list(fields)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        raise NotImplementedError


class Statements(_Executable):
    """A sequence of executable statements."""

    def __init__(self, statements: Sequence[_Executable]):
        super().__init__()
        self.statements = statements

    def _call(self, record: Record) -> None:
        for statement in self.statements:
            statement(record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        for statement in self.statements:
            statement._update_fields(fields)

    def __str__(self):
        return "\n".join(str(statement) for statement in self.statements)

    def append(self, _Executable):
        self.statements.append(_Executable)


class Assignment(_Executable):
    """Assign a value to a field."""

    def __init__(self, name: str, value: ProgramElement):
        super().__init__()
        self.name = name
        self.value = string_encode(value)

    def _call(self, record: Record) -> None:
        record[self.name] = self.value(record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        fields.add(self.name)

    def __str__(self):
        return f"{{{self.name}}} = {self.value}"


class BareExpression(_Executable):
    """An expression used as a statement."""

    def __init__(self, inner: ProgramElement):
        super().__init__()
        self.inner = inner

    def _call(self, record: Record) -> None:
        self.inner(record)
        return None

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        pass

    def __str__(self):
        return str(self.inner)


class Rule(_Executable):
    """Conditionally execute some statements"""

    def __init__(
        self,
        ifthens: Iterable[Tuple[ProgramElement, _Executable]],
        else_=Optional[_Executable],
    ):
        super().__init__()
        self.ifthens = [
            (as_boolean(condition), statement) for condition, statement in ifthens
        ]
        if not self.ifthens:
            raise ValueError("Must specify at least one condition in a rule.")
        self.else_ = else_

    def _call(self, record: Record) -> None:
        for condition, statement in self.ifthens:
            if condition(record):
                statement(record)
                return
        if self.else_ is not None:
            self.else_(record)

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        for _, statement in self.ifthens:
            statement._update_fields(fields)
        if self.else_ is not None:
            self.else_._update_fields(fields)

    def __str__(self):
        ifthen, *elifthens = self.ifthens
        condition, statement = ifthen
        lines = [f"if {condition} then\n{statement}"]
        for condition, statement in elifthens:
            lines.append(f"elif {condition} then\n{statement}")
        if self.else_ is not None:
            lines.append(f"else\n{self.else_}")
        lines.append("fi")
        return "\n".join(lines)


class Fields(_Executable):
    """Specify an explicit set of fields, dropping all others."""

    def __init__(self, fields: Iterable[str]):
        super().__init__()
        self._fields = OrderedSet(fields)

    def _call(self, record: Record) -> None:
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
    def __init__(self, statements: _Executable):
        super().__init__()
        self.statements = statements

    def _call(self, record: Record) -> None:
        self.statements(record)

    def transform(self, record: Record) -> Record:
        """Return a transformed copy of a record."""
        new_record = record.copy()
        self(new_record)
        return new_record

    def _update_fields(self, fields: OrderedSet[str]) -> None:
        self.statements._update_fields(fields)

    def __str__(self):
        return f"{self.statements}\n"
