from __future__ import annotations

from enum import StrEnum
from typing import Any, Callable, Final, Generator, TypeVar, TypeVarTuple, Unpack

import parsy
from tcstc.models.pointer import Pointer

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


def token(*tokens: str) -> parsy.Parser[str]:
    return parsy.string_from(*tokens, transform=str.upper) << whitespace_parser


def enum(*items: _E) -> parsy.Parser[_E]:
    lookup = {item.value: item for item in items}
    return token(*lookup.keys()).map(lambda value: lookup[value])


whitespace_lines: Final = Pointer(0)


@parsy.generate
def whitespace_parser() -> Generator[Any, Any, None]:
    whitespace = yield from parse(parsy.regex(r"[ \t\r\n]*"))
    whitespace_lines.value = whitespace.count("\n")
