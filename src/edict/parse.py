"""Parse Edict files."""
from __future__ import annotations

import ast
import decimal
import re
from typing import TYPE_CHECKING, Any, Callable, Union

import lark
import pkg_resources

from edict.types import (
    Assignment,
    ConditionEquation,
    ConditionExpression,
    Operator,
    Program,
    Rule,
)

if TYPE_CHECKING:
    import os

__all__ = ["parse", "parse_file"]


def parse(text: str) -> Program:
    parser = _get_parser()
    return parser.parse(text)


def parse_file(file: Union[str, bytes, os.PathLike]) -> Program:
    parser = _get_parser()
    with open(file, "r") as f:
        return parser.parse(f.read())


def _get_parser():
    grammar_file = pkg_resources.resource_filename("edict", "edict.lark")
    lexer_callbacks = {
        "FALSE": _make_const_lexer_callback(False),
        "TRUE": _make_const_lexer_callback(True),
        "NUMBER": _make_lexer_callback(decimal.Decimal),
        "QUOTED_STRING": _make_lexer_callback(ast.literal_eval),
        "REGEX_STRING": _make_lexer_callback(_eval_regex),
    }
    return lark.Lark.open(
        grammar_file,
        parser="lalr",
        transformer=_TransformPipeline(),
        lexer_callbacks=lexer_callbacks,
    )


def _make_const_lexer_callback(x: Any) -> Callable[[lark.Token], lark.Token]:
    def _callback(token: lark.Token) -> lark.Token:
        return lark.Token.new_borrow_pos(token.type, x, token)

    return _callback


def _make_lexer_callback(f: Callable[[str], Any]) -> Callable[[lark.Token], lark.Token]:
    def _callback(token: lark.Token) -> lark.Token:
        return lark.Token.new_borrow_pos(token.type, f(token.value), token)

    return _callback


def _eval_regex(regex: str) -> re.Pattern:
    return re.compile(ast.literal_eval("".join(('"', regex[1:-1], '"'))))


_DATA_TYPES = {"ESCAPED_STRING": "STRING"}


# TODO: Report line numbers in errors
# Use @v_args(meta=True) along with propagate_positions=True
class _TransformPipeline(lark.Transformer):
    def __init__(self):
        self._assigned_fields = set()
        self._context = {"case_sensitive": True}

    def header_case_sensitive_match(self, args):
        (t_value,) = args
        self._context["case_sensitive"] = t_value.value
        # TODO: Implement case insensitivity in transform.
        raise NotImplementedError

    def header_default_field(self, args):
        (t_field,) = args
        self._context["default_field"] = t_field.value

    def headers(self, args):
        assert all(x is None for x in args), "Not all headers were processed"
        return self._context

    def condition_equation(self, args):
        t_field, t_op, t_value = args

        return ConditionEquation(
            field=t_field.value, operator=Operator[t_op.type], data=t_value.value,
        )

    def simple_condition(self, args):
        (t_value,) = args
        try:
            field = self._context["default_field"]
        except KeyError:
            raise ValueError("Must specify 'default_field' when using ':' conditions")
        return ConditionExpression(
            checks=(
                ConditionEquation(
                    field=field, operator=Operator.MATCH, data=t_value.value
                ),
            )
        )

    def regular_condition(self, args):
        return ConditionExpression(checks=tuple(args))

    def conditions(self, args):
        return args

    def assignment(self, args):
        t_field, t_value = args
        field = t_field.value
        self._assigned_fields.add(field)
        return Assignment(field=t_field.value, value=t_value.value)

    def assignments(self, args):
        return args

    def rule(self, args):
        conditions, assignments = args
        return Rule(conditions, assignments)

    def rules(self, args):
        return args

    def start(self, args):
        context, rules = args
        return Program(
            context=context, rules=rules, assigned_fields=tuple(self._assigned_fields)
        )


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(description="Parse an Edict file.")
    argparser.add_argument("file", type=str, help="Edict file")
    args = argparser.parse_args()
    program = parse_file(args.file)
    print(program)
