from dataclasses import dataclass
from enum import StrEnum
from typing import TypeAlias


class Keyword(StrEnum):
    AND = "AND"
    AND_THEN = "AND_THEN"
    ARRAY = "ARRAY"
    AT = "AT"
    CASE = "CASE"
    CONSTANT = "CONSTANT"
    DO = "DO"
    ELSE = "ELSE"
    ELSIF = "ELSIF"
    END_CASE = "END_CASE"
    END_FUNCTION = "END_FUNCTION"
    END_FUNCTION_BLOCK = "END_FUNCTION_BLOCK"
    END_GET = "END_GET"
    END_IF = "END_IF"
    END_INTERFACE = "END_INTERFACE"
    END_PROGRAM = "END_PROGRAM"
    END_PROPERTY = "END_PROPERTY"
    END_SET = "END_SET"
    END_STRUCT = "END_STRUCT"
    END_TYPE = "END_TYPE"
    END_VAR = "END_VAR"
    FALSE = "FALSE"
    FUNCTION = "FUNCTION"
    FUNCTION_BLOCK = "FUNCTION_BLOCK"
    GET = "GET"
    IF = "IF"
    INTERFACE = "INTERFACE"
    MOD = "MOD"
    NOT = "NOT"
    OF = "OF"
    OR = "OR"
    OR_ELSE = "OR_ELSE"
    POINTER = "POINTER"
    PRIVATE = "PRIVATE"
    PROGRAM = "PROGRAM"
    PROPERTY = "PROPERTY"
    PROTECTED = "PROTECTED"
    PUBLIC = "PUBLIC"
    SET = "SET"
    STRUCT = "STRUCT"
    TO = "TO"
    TRUE = "TRUE"
    TYPE = "TYPE"
    VAR = "VAR"
    VAR_GLOBAL = "VAR_GLOBAL"
    VAR_IN_OUT = "VAR_IN_OUT"
    VAR_INPUT = "VAR_INPUT"
    VAR_INST = "VAR_INST"
    VAR_OUTPUT = "VAR_OUTPUT"
    XOR = "XOR"


class Symbol(StrEnum):
    ASSIGN = ":="
    ASSIGN_OUT = "=>"
    ASSIGN_REF = "REF="
    CARET = "^"
    COLON = ":"
    COMMA = ","
    DIV = "/"
    DOT = "."
    EQ = "="
    GE = ">"
    GEQ = ">="
    LE = "<"
    LEQ = "<="
    MINUS = "-"
    MULT = "*"
    NEQ = "<>"
    PLUS = "+"
    PTR_DOT = "^."
    SEMI = ";"
    LPAREN = "("
    RPAREN = ")"
    LSQUARE = "["
    RSQUARE = "]"
    LCURLY = "{"
    RCURLY = "}"
    INPUT = "%I*"
    OUTPUT = "%Q*"


@dataclass
class Preprocessor:
    text: str


@dataclass
class BlockComment:
    comment: str


@dataclass
class LineComment:
    comment: str


@dataclass
class Identifier:
    name: str


@dataclass
class String:
    string: str


@dataclass
class Integer:
    value: int
    base: int


@dataclass
class Time:
    millis: int


@dataclass
class Whitespace:
    lines: int


Token: TypeAlias = (
    Keyword
    | Symbol
    | Preprocessor
    | BlockComment
    | LineComment
    | Identifier
    | String
    | Integer
    | Time
    | Whitespace
)
