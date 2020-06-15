"""Parse edict files."""
from __future__ import annotations

import operator
import re
from decimal import Decimal
from typing import TYPE_CHECKING, Any, Callable, Union

import lark
import pkg_resources

from edict import program

if TYPE_CHECKING:
    import os

__all__ = ["parse", "parse_file"]


def parse(text: str) -> program.Program:
    parser = _get_parser()
    return parser.parse(text)


def parse_file(file: Union[str, bytes, os.PathLike]) -> program.Program:
    parser = _get_parser()
    with open(file, "r") as f:
        return parser.parse(f.read())


def _get_parser():
    grammar_file = pkg_resources.resource_filename("edict", "edict.lark")
    decode_quoted_string_callback = _make_lexer_callback(_decode_quoted_string)
    lexer_callbacks = {
        "FALSE": _make_const_lexer_callback(False),
        "TRUE": _make_const_lexer_callback(True),
        "NUMBER": _make_lexer_callback(Decimal),
        "QUOTED_STRING": decode_quoted_string_callback,
        "BRACED_IDENTIFIER": decode_quoted_string_callback,
        "REGEX_STRING": _make_lexer_callback(_decode_regex_string),
    }
    return lark.Lark.open(
        grammar_file,
        parser="lalr",
        transformer=_TransformToProgram(),
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
        return chr(int(s[2:], 16))
    return _ESCAPE_SEQUENCES[s]


_DATA_TYPES = {"ESCAPED_STRING": "STRING"}

_OPERATOR_FUNCTIONS = {
    "EQ": operator.eq,
    "NE": operator.ne,
    "LT": operator.lt,
    "LE": operator.le,
    "GT": operator.gt,
    "GE": operator.ge,
}


def _decimal_mod(a: Decimal, b: Decimal) -> Decimal:
    """a % b with sign matching b, same as mod on python number types."""
    # Decimal % matches the sign of a instead
    return (a % b).copy_sign(b)


class _TransformToProgram(lark.Transformer):
    """Transform to a structured Edict program"""

    def __init__(self):
        self._context = {}

    def _header_match_case_insensitive(self, value):
        if value.dtype != program.DataType.BOOLEAN:
            raise ValueError(f"Expected BOOLEAN but got {value.dtype}")
        self._context["case_insensitive"] = value.value

    def _header_default_field(self, identifier):
        if identifier.dtype != program.DataType.STRING:
            raise ValueError(f"Expected STRING but got {identifier.dtype}")
        self._context["default_field"] = program.Identifier(identifier.value)

    def _header_output_fields(self, *fields):
        field_names = []
        for field in fields:
            if field.dtype != program.DataType.STRING:
                raise ValueError(f"Expected STRING but got {field.dtype}")
            field_names.append(field.value)
        self._context["output_fields"] = field_names

    def header_call(self, args):
        name, *fargs = args
        assert all(isinstance(farg, program.Literal) for farg in fargs)
        {
            "match_case_insensitive": self._header_match_case_insensitive,
            "default_field": self._header_default_field,
            "output_fields": self._header_output_fields,
        }[name](*fargs)

    def header(self, args):
        return self._context

    def literal(self, args):
        (t_value,) = args
        if t_value.type == "QUOTED_STRING":
            assert isinstance(t_value.value, str)
            dtype = program.DataType.STRING
        elif t_value.type == "NUMBER":
            assert isinstance(t_value.value, Decimal)
            dtype = program.DataType.NUMBER
        elif t_value.type == "REGEX_STRING":
            assert isinstance(t_value.value, str)
            dtype = program.DataType.REGEX
        elif t_value.type in ("TRUE", "FALSE"):
            assert isinstance(t_value.value, bool)
            dtype = program.DataType.BOOLEAN
        else:
            assert False, f"Unexpected type: {t_value.type}"

        return program.Literal(value=t_value.value, dtype=dtype)

    def identifier(self, args):
        (t_name,) = args
        assert isinstance(t_name.value, str)
        return program.Identifier(t_name.value)

    def _as_boolean(self, value: program.ProgramElement) -> program.ProgramElement:
        """Try to convert the given value to a Boolean

        Applies implicit matching to string and regex objects."""
        if value.dtype in (program.DataType.STRING, program.DataType.REGEX):
            default_field = self._context.get("default_field")
            if default_field is None:
                raise ValueError("Must set `default_field` to use implicit matching.")
            return self._make_match(pattern=value, string=default_field)
        return value

    def call(self, args):
        t_name, *fargs = args
        return program.function_call(t_name.value, fargs)

    def u_expr(self, args):
        if len(args) == 1:
            return args[0]

        t_op, inner = args
        if t_op.value == "+":
            return inner
        return program.UnaryMinus(inner)

    def m_expr(self, args):
        if len(args) == 1:
            return args[0]

        left, t_op, right = args
        if t_op.value == "*":
            op = operator.mul
        elif t_op.value == "/":
            op = operator.truediv
        elif t_op.value == "%":
            op = _decimal_mod
        else:
            assert False, f"Unexpected operator: {t_op}"
        return program.BinaryOperator(left, right, op, program.DataType.NUMBER)

    def a_expr(self, args):
        if len(args) == 1:
            return args[0]

        left, t_op, right = args
        if t_op.value == "+":
            op = operator.add
            dtype = program.DataType.NUMBER
        elif t_op.value == "-":
            op = operator.sub
            dtype = program.DataType.NUMBER
        elif t_op.value == ".":
            op = operator.concat
            dtype = program.DataType.STRING
        else:
            assert False, f"Unexpected operator: {t_op}"
        return program.BinaryOperator(left, right, op, dtype)

    def comp_expr(self, args):
        if len(args) == 1:
            return args[0]

        left, t_op, right = args
        if t_op.type == "MATCH":
            return self._make_match(pattern=right, string=left)
        else:
            return program.ValueComparisonOperator(
                left=left, right=right, op=_OPERATOR_FUNCTIONS[t_op.type]
            )

    def _make_match(
        self, pattern: program.ProgramElement, string: program.ProgramElement
    ) -> Union[program.Match, program.SubString]:
        case_insensitive = self._context.get("case_insensitive", False)
        if isinstance(pattern, program.Literal):
            if pattern.dtype == program.DataType.STRING:
                return program.SubString(
                    substring=pattern, string=string, case_insensitive=case_insensitive
                )
            if pattern.dtype == program.DataType.REGEX:
                return program.Match(
                    pattern=pattern, string=string, case_insensitive=case_insensitive
                )
        raise ValueError("Match pattern must be a STRING or REGEX literal")

    def not_expr(self, args):
        if len(args) == 1:
            return args[0]

        _, inner = args
        inner = self._as_boolean(inner)
        return program.UnaryNot(inner)

    def and_expr(self, args):
        if len(args) == 1:
            return args[0]

        args = [self._as_boolean(arg) for arg in args]
        return program.Conjunction(args)

    def or_expr(self, args):
        if len(args) == 1:
            return args[0]

        args = [self._as_boolean(arg) for arg in args]
        return program.Disjunction(args)

    def assignment(self, args):
        identifier, value = args
        return program.Assignment(name=identifier.name, value=value)

    def rule(self, args):
        ifthens = args
        if ifthens[-1][0] is None:
            ifthens, final = ifthens[:-1], ifthens[-1]
            _, else_ = final
        else:
            else_ = None
        return program.Rule(ifthens, else_)

    def rule_ifthen(self, args):
        condition, statements = args
        return (self._as_boolean(condition), statements)

    def rule_else(self, args):
        (statements,) = args
        return (None, statements)

    def statements(self, args):
        if len(args) == 1:
            return args[0]
        return program.Statements(args)

    def start(self, args):
        header, statements = args
        if not isinstance(statements, program.Statements):
            statements = program.Statements([statements])
        try:
            output_fields = header["output_fields"]
        except KeyError:
            pass
        else:
            statements.append(program.Fields(output_fields))
        return program.Program(statements=statements)


if __name__ == "__main__":
    import argparse

    argparser = argparse.ArgumentParser(description="Parse an edict file.")
    argparser.add_argument("file", type=str, help="Edict file")
    args = argparser.parse_args()
    p = parse_file(args.file)
    print(p)
