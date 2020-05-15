"""Transform records according to an edict program."""
from __future__ import annotations

import operator
from decimal import Decimal
from typing import Any, Callable, Dict, Sequence, overload

from edict.types import (
    Assignment,
    ConditionEquation,
    ConditionExpression,
    Operator,
    Program,
    Record,
)

if __debug__:
    import re


class Transformer:
    """Transform records according to an Edict program."""

    def __init__(self, program: Program):
        self.program = program
        self.context = program.context

    def transform(self, record: Record) -> Record:
        """Transform a record in-place"""
        for rule in self.program.rules:
            if self._satisfies_conditions(rule.conditions, record):
                _apply_assignments(rule.assignments, record)
        return record

    def _satisfies_conditions(
        self, conditions: Sequence[ConditionExpression], record: Record
    ) -> bool:
        """Check whether the given record satisfies any of the given conditions."""
        return any(
            self._satisfies_condition(condition, record) for condition in conditions
        )

    def _satisfies_condition(
        self, condition: ConditionExpression, record: Record
    ) -> bool:
        """Check whether the given record satisfies the given condition."""
        return all(
            self._satisfies_equation(equation, record) for equation in condition.checks
        )

    def _satisfies_equation(self, equation: ConditionEquation, record: Record) -> bool:
        field = equation.field
        if field is None:
            field = self.context["default_field"]
        try:
            value_str = record[field]
        except KeyError:
            return False

        operator = equation.operator

        if operator == Operator.MATCH:
            pattern = equation.data
            string = value_str
            if isinstance(pattern, str):
                case_insensitive = self.context.get("case_insensitive", False)
                if case_insensitive:
                    string = string.lower()
                # pattern already lowered
                return pattern in string
            else:
                assert isinstance(pattern, re.Pattern)
                # lhs compiled with IGNORECASE if case_insensitive
                return bool(pattern.search(string))

        compare_values_fn = _VALUE_COMPARISONS.get(operator)
        if compare_values_fn is not None:
            rhs = equation.data
            assert not isinstance(rhs, re.Pattern)
            lhs = _parse_like(value_str, rhs)
            return compare_values_fn(lhs, rhs)

        raise AssertionError(f"Unknown operator {operator}")


_VALUE_COMPARISONS: Dict[Operator, Callable[[Any, Any], bool]] = {
    Operator.EQ: operator.eq,
    Operator.NE: operator.ne,
    Operator.LT: operator.lt,
    Operator.LE: operator.le,
    Operator.GT: operator.gt,
    Operator.GE: operator.ge,
}


@overload
def _parse_like(s: str, x: str) -> str:
    ...


@overload
def _parse_like(s: str, x: Decimal) -> Decimal:
    ...


def _parse_like(s, x):
    if isinstance(x, str):
        return s
    if isinstance(x, Decimal):
        return Decimal(s)
    raise AssertionError(f"Unexpected type {type(x)}")


def _apply_assignments(assignments: Sequence[Assignment], record: Record) -> None:
    """Apply assignments to a rule in-place."""
    for assignment in assignments:
        record[assignment.field] = assignment.value
