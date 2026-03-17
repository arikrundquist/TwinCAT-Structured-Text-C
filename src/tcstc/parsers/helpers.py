from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable, Generator, TypeVar, TypeVarTuple, Unpack

import parsy

_T = TypeVar("_T")
_E = TypeVar("_E", bound=StrEnum)
_TT = TypeVarTuple("_TT")


def parse(parser: parsy.Parser[_T]) -> Generator[Any, Any, _T]:
    value: _T = yield parser
    return value


def map(
    parser: parsy.Parser[tuple[Unpack[_TT]]], func: Callable[[Unpack[_TT]], _T]
) -> parsy.Parser[_T]:
    return parser.map(lambda values: func(*values))


def case_insensitive(*strings: str) -> parsy.Parser[str]:
    return parsy.string_from(*strings, transform=str.upper)


def symbol(*items: _E) -> parsy.Parser[_E]:
    lookup = {item.value: item for item in items}
    return case_insensitive(*lookup.keys()).map(lambda value: lookup[value])


def symbols(Symbols: type[_E]) -> parsy.Parser[_E]:
    return symbol(*Symbols)


def keyword(*items: _E) -> parsy.Parser[_E]:
    return symbol(*items) << parsy.regex("(?![a-zA-Z_])")


def keywords(Keywords: type[_E]) -> parsy.Parser[_E]:
    return keyword(*Keywords) << parsy.regex("(?![a-zA-Z_])")


@parsy.generate
def whitespace_parser() -> Generator[Any, Any, int]:
    whitespace = yield from parse(parsy.regex(r"[ \t\r\n]+"))
    return whitespace.count("\n")
