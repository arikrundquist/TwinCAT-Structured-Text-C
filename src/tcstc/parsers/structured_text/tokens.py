from __future__ import annotations

from typing import Any, Generator

import parsy
from tcstc.models.structured_text import tokens as st
from tcstc.parsers.helpers import (
    keywords,
    parse,
    symbols,
    whitespace_parser,
)


@parsy.generate
def keyword_parser() -> Generator[Any, Any, st.Keyword]:
    parser = keywords(st.Keyword)
    value = yield from parse(parser)
    return value


@parsy.generate
def symbol_parser() -> Generator[Any, Any, st.Symbol]:
    parser = symbols(st.Symbol)
    value = yield from parse(parser)
    return value


@parsy.generate
def preprocessor_parser() -> Generator[Any, Any, st.Preprocessor]:
    parser = parsy.regex(r"\{[^}]*\}")
    text = yield from parse(parser)
    return st.Preprocessor(text)


@parsy.generate
def block_comment_parser() -> Generator[Any, Any, st.BlockComment]:
    parser = parsy.regex(r"\(\*((?!\*\)).)*\*\)")
    comment = yield from parse(parser)
    return st.BlockComment(comment)


@parsy.generate
def line_comment_parser() -> Generator[Any, Any, st.LineComment]:
    parser = parsy.regex(r"//[^\n]*")
    comment = yield from parse(parser)
    return st.LineComment(comment)


@parsy.generate
def identifier_parser() -> Generator[Any, Any, st.Identifier]:
    parser = parsy.regex("[_a-zA-Z][_a-zA-Z0-9]*")
    name = yield from parse(parser)
    return st.Identifier(name)


@parsy.generate
def string_parser() -> Generator[Any, Any, st.String]:
    parser = parsy.regex("([^$']|$[0-9A-Fa-f]{2}|$[$'LlNnPpRrTt])*")
    yield parsy.string("'")
    string = yield from parse(parser)
    yield parsy.string("'")
    return st.String(string)


@parsy.generate
def integer_parser() -> Generator[Any, Any, st.Integer]:
    base_2 = (2, "[01]+")
    base_8 = (8, "[0-7]+")
    base_10 = (10, "[0-9]+")
    base_16 = (16, "[0-9A-Fa-f]+")

    base_2_parser = parsy.string("2#").map(lambda _: base_2)
    base_8_parser = parsy.string("8#").map(lambda _: base_8)
    base_16_parser = parsy.string("16#").map(lambda _: base_16)

    base_parser = (base_2_parser | base_8_parser | base_16_parser).optional(base_10)
    base, regex = yield from parse(base_parser)

    value_parser = parsy.regex(regex)
    value = yield from parse(value_parser)

    return st.Integer(int(value, base=base), base=base)


@parsy.generate
def time_parser() -> Generator[Any, Any, st.Time]:
    def component_parser(unit: str) -> parsy.Parser[int]:
        return (
            parsy.regex("[0-9]+").map(int)
            << parsy.string(unit, str.upper)
            << parsy.regex("(?![a-zA-Z])")
        ).optional(0)

    yield parsy.string("T#", str.upper)
    millis = yield from parse(component_parser("d"))
    millis = 24 * millis + (yield from parse(component_parser("h")))
    millis = 60 * millis + (yield from parse(component_parser("m")))
    millis = 60 * millis + (yield from parse(component_parser("s")))
    millis = 1000 * millis + (yield from parse(component_parser("ms")))

    return st.Time(millis)


@parsy.generate
def whitespace() -> Generator[Any, Any, st.Whitespace]:
    value = yield from parse(whitespace_parser)
    return st.Whitespace(value)


parser = (
    whitespace_parser.optional()
    >> (
        keyword_parser
        | preprocessor_parser
        | block_comment_parser
        | line_comment_parser
        | string_parser
        | integer_parser
        | time_parser
        | whitespace
        | identifier_parser
        | symbol_parser
    ).many()
)
