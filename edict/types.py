"""Data types used by the edict python package."""
from __future__ import annotations

from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    Iterable,
    NamedTuple,
    Optional,
    Sequence,
    Tuple,
    Union,
)

if TYPE_CHECKING:
    from decimal import Decimal
    from re import Pattern


__all__ = [
    "Assignment",
    "AssignmentTerm",
    "ConditionEquation",
    "ConditionExpression",
    "Operator",
    "Program",
    "RecordStream",
    "Rule",
]


class Operator(Enum):
    EQ = 1
    NE = 2
    LT = 3
    LE = 4
    GT = 5
    GE = 6
    MATCH = 7


class ConditionEquation(NamedTuple):
    field: Optional[str]
    operator: Operator
    data: Union[str, Decimal, Pattern]


class ConditionExpression(NamedTuple):
    checks: Sequence[ConditionEquation]


class Assignment(NamedTuple):
    field: str
    terms: Sequence[AssignmentTerm]


class AssignmentTerm(NamedTuple):
    is_field: bool
    value: str


class Rule(NamedTuple):
    conditions: Sequence[ConditionExpression]
    assignments: Sequence[Assignment]


class Program(NamedTuple):
    context: Dict[str, Any]
    rules: Sequence[Rule]
    assigned_fields: Tuple[str, ...]


Record = Dict[str, str]


class RecordStream(NamedTuple):
    fields: Tuple[str, ...]
    records: Iterable[Record]
