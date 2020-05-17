"""Parse edict files."""
from __future__ import annotations

import decimal
import re
from typing import TYPE_CHECKING, Any, Callable, Union

import lark
import pkg_resources

from edict.types import (
    Assignment,
    AssignmentTerm,
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
    decode_quoted_string_callback = _make_lexer_callback(_decode_quoted_string)
    lexer_callbacks = {
        "FALSE": _make_const_lexer_callback(False),
        "TRUE": _make_const_lexer_callback(True),
        "NUMBER": _make_lexer_callback(decimal.Decimal),
        "QUOTED_STRING": decode_quoted_string_callback,
        "REGEX_STRING": _make_lexer_callback(_decode_regex_string),
        "FIELD_STRING": decode_quoted_string_callback,
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


def _decode_regex_string(s: str) -> str:
    return re.sub(r"\/", "/", s[1:-1])


def _decode_field_string(s: str) -> str:
    return re.sub(r"\}", "}", s[1:-1])


def _decode_quoted_string(s: str) -> str:
    """Decode all edict escape sequences in the given string."""
    return _STRING_ESCAPE_PATTERN.sub(_escape_replace, s[1:-1])


_ESCAPE_SEQUENCES = {
    "\\\\": "\\",
    r"\}": "}",
    r"\a": "\a",
    r"\b": "\b",
    r"\f": "\f",
    r"\n": "\n",
    r"\r": "\r",
    r"\t": "\t",
    r"\v": "\v",
}

_STRING_ESCAPE_PATTERN = re.compile(
    "|".join(
        [re.escape(k) for k in _ESCAPE_SEQUENCES.keys()]
        + [r"\\x[0-9A-Fa-f]{2}", r"\\u[0-9A-Fa-f]{4}", r"\\U[0-9A-Fa-f]{6}"]
    )
)


def _escape_replace(m: re.Match) -> str:
    s = m.group(0)
    if s.startswith(r"\x"):
        return chr(hex(s[2:], 16))
    return _ESCAPE_SEQUENCES[s]


_DATA_TYPES = {"ESCAPED_STRING": "STRING"}


# TODO: Report line numbers in errors
# Use @v_args(meta=True) along with propagate_positions=True
class _TransformPipeline(lark.Transformer):
    def __init__(self):
        self._assigned_fields = set()
        self._context = {}

    def header_case_insensitive_match(self, args):
        (t_value,) = args
        self._context["case_insensitive"] = t_value.value

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

    def match_value(self, args):
        (t_value,) = args
        case_insensitive = self._context.get("case_insensitive", False)

        if t_value.type == "REGEX_STRING":
            flags = re.IGNORECASE if case_insensitive else 0
            value = re.compile(t_value.value, flags=flags)
        else:
            assert t_value.type == "QUOTED_STRING"
            value = t_value.lower()
        return lark.Token.new_borrow_pos(t_value.type, value, t_value)

    def conditions(self, args):
        if len(args) == 1:
            (t_value,) = args
            if isinstance(t_value, lark.Token):
                if t_value.value:
                    return [ConditionExpression(checks=())]
                else:
                    return []
        return args

    def assignment_term(self, args):
        (t_value,) = args
        return AssignmentTerm(
            is_field=t_value.type in ("FIELD_STRING", "WORD"), value=t_value.value
        )

    def assignment(self, args):
        t_field, *terms = args
        field = t_field.value
        self._assigned_fields.add(field)
        return Assignment(field=t_field.value, terms=terms)

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

    argparser = argparse.ArgumentParser(description="Parse an edict file.")
    argparser.add_argument("file", type=str, help="Edict file")
    args = argparser.parse_args()
    program = parse_file(args.file)
    print(program)
