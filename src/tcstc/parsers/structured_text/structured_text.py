from __future__ import annotations

from enum import StrEnum
from pathlib import Path
from typing import (
    Any,
    Callable,
    Final,
    Generator,
    TypeAlias,
    TypeVar,
)

import parsy
from tcstc.models.pointer import Pointer
from tcstc.models.structured_text import structured_text as st
from tcstc.parsers.helpers import map, parse

_E = TypeVar("_E", bound=StrEnum)
_T = TypeVar("_T")


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


def sep_trailing_comma(parser: parsy.Parser[_T]) -> parsy.Parser[list[_T]]:
    comma_parser = token(",")
    return parser.sep_by(comma_parser) << comma_parser.optional()


identifier_parser = (
    parsy.regex("[_a-zA-Z][_a-zA-Z0-9]*").map(st.Identifier) << whitespace_parser
)

comment_parser = parsy.regex(r"//[^\n]*").map(st.Comment) << whitespace_parser

constant_parser = token("CONSTANT").optional().map(bool)


@parsy.generate
def string_parser() -> Generator[Any, Any, st.String]:
    contents_parser = parsy.regex("([^']|$[0-9A-Fa-f]{2}|$[$'LlNnPpRrTt])*")

    yield token("'")
    contents = yield from parse(contents_parser)
    yield token("'")
    return st.String(contents)


@parsy.generate
def integer_parser() -> Generator[Any, Any, st.Integer]:
    base_2 = (2, "[01]+")
    base_8 = (8, "[0-7]+")
    base_10 = (10, "[0-9]+")
    base_16 = (16, "[0-9A-Fa-f]+")

    base_2_parser = token("2#").map(lambda _: base_2)
    base_8_parser = token("8#").map(lambda _: base_8)
    base_16_parser = token("16#").map(lambda _: base_16)

    base_parser = (base_2_parser | base_8_parser | base_16_parser).optional(base_10)
    base, regex = yield from parse(base_parser)

    value_parser = parsy.regex(regex)
    value = yield from parse(value_parser)
    yield whitespace_parser

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
    yield whitespace_parser

    return st.Time(millis)


@parsy.generate
def attribute_parser() -> Generator[Any, Any, st.Attribute]:
    name_parser = parsy.regex("[^']+")
    value_parser = (parsy.regex(r"'\s*:=\s*'") >> parsy.regex("[^']+")).optional()

    yield token("{attribute '")
    name = yield from parse(name_parser)
    value = yield from parse(value_parser)
    yield token("'}")

    return st.Attribute(name) if value is None else st.AttributeEq(name, value)


attributes_parser = whitespace_parser >> (attribute_parser | comment_parser).many()

enum_subtype_parser = token(
    "UINT",
    "SINT",
    "USINT",
    "DINT",
    "UDINT",
    "LINT",
    "ULINT",
    "BYTE",
    "WORD",
    "DWORD",
    "LWORD",
)


@parsy.generate
def enum_member_parser() -> Generator[Any, Any, st.EnumElement]:
    value_parser = (token(":=") >> integer_parser).optional()

    name = yield from parse(identifier_parser)
    value = yield from parse(value_parser)

    return st.EnumElement(name, value.value if value is not None else value)


@parsy.generate
def enum_parser() -> Generator[Any, Any, Callable[[st.Identifier], st.Enum]]:
    enum_members_parser = enum_member_parser.sep_by(token(","))
    enum_type_parser = enum_subtype_parser.optional()

    yield token("(")
    members = yield from parse(enum_members_parser)
    yield token(")")
    type = yield from parse(enum_type_parser)
    yield token(";")

    return lambda name: st.Enum(name, type, members)


@parsy.generate
def variable_linkage_parser() -> Generator[Any, Any, Callable[[st.Type], st.Linked]]:
    Linker: TypeAlias = Callable[[st.Type], st.Linked]
    input_linker: Linker = st.LinkedIn
    output_linker: Linker = st.LinkedOut
    noop_linker: Linker = lambda x: x

    input_parser: parsy.Parser[Linker] = token("%I*").map(lambda _: input_linker)
    output_parser: parsy.Parser[Linker] = token("%Q*").map(lambda _: output_linker)

    linkage_parser = (token("AT") >> (input_parser | output_parser)).optional(
        noop_linker
    )
    linker = yield from parse(linkage_parser)

    return linker


@parsy.generate
def array_parser() -> Generator[Any, Any, st.Type]:
    yield token("ARRAY")
    yield token("[")
    bounds_parser = parsy.seq(integer_parser, token("..") >> integer_parser)
    unbounded_parser = token("*").map(lambda _: None)
    bounds = yield from parse(bounds_parser | unbounded_parser)
    yield token("]")
    yield token("OF")
    type = yield from parse(type_parser)

    if bounds is None:
        return st.DynamicArray(type)

    low, high = bounds
    return st.BoundedArray(type, low, high)


@parsy.generate
def type_parser() -> Generator[Any, Any, st.Type]:
    base_parser = identifier_parser
    reference_parser = (
        token("REFERENCE") >> token("TO") >> type_parser.map(st.Reference)
    )
    pointer_parser = token("POINTER") >> token("TO") >> type_parser.map(st.Reference)
    recursive_parser = array_parser | reference_parser | pointer_parser | base_parser

    type = yield from parse(recursive_parser)
    return type


@parsy.generate
def identifier_assignment_parser() -> (
    Generator[Any, Any, tuple[st.Identifier, st.Expression]]
):
    name = yield from parse(identifier_parser << token(":="))
    value = yield from parse(expression_parser)

    return name, value


@parsy.generate
def _expression_parser_0() -> Generator[Any, Any, st.Expression]:
    """terms and parenthesized expressions"""
    initializer_parser = (
        token("(")
        >> sep_trailing_comma(identifier_assignment_parser).map(st.Initializer)
        << token(")")
    )
    term_parser = (
        initializer_parser
        | time_parser
        | integer_parser
        | string_parser
        | identifier_parser
    )
    paren_parser = token("(") >> expression_parser << token(")")

    return (yield from parse(term_parser | paren_parser))


@parsy.generate
def _func_call_parser() -> Generator[Any, Any, Callable[[st.Expression], st.FuncCall]]:
    kwarg_parser = parsy.seq(
        identifier_parser,
        token(":=").map(lambda _: False) | token("=>").map(lambda _: True),
        expression_parser.optional(),
    )
    arg_parser = expression_parser
    args_kwargs_parser = sep_trailing_comma(kwarg_parser | arg_parser)

    yield token("(")
    args_kwargs = yield from parse(args_kwargs_parser)
    yield token(")")

    args = list[st.Expression]()
    kwargs = list[st.Kwarg]()

    for item in args_kwargs:
        if not isinstance(item, st.ASTNode):
            name, out, value = item
            kwargs.append(st.Kwarg(name, value, out))
            continue

        assert len(kwargs) == 0
        args.append(item)

    return lambda expr: st.FuncCall(expr, args, kwargs)


@parsy.generate
def _record_parser() -> Generator[Any, Any, Callable[[st.Expression], st.Record]]:
    ptr_parser = token(".").map(lambda _: False) | token("^.").map(lambda _: True)

    ptr = yield from parse(ptr_parser)
    field = yield from parse(identifier_parser)

    return lambda expr: st.Record(expr, field, ptr)


@parsy.generate
def _index_parser() -> Generator[Any, Any, Callable[[st.Expression], st.Index]]:
    yield token("[")
    index = yield from parse(expression_parser)
    yield token("]")
    return lambda expr: st.Index(expr, index)


@parsy.generate
def _expression_parser_1() -> Generator[Any, Any, st.Expression]:
    """record access, array index, function calls"""
    head = yield from parse(_expression_parser_0)
    tail = yield from parse((_func_call_parser | _record_parser | _index_parser).many())

    for modifier in tail:
        head = modifier(head)

    return head


def _make_binary_ops(
    lhs_parser: parsy.Parser[st.Expression],
    rhs_parser: parsy.Parser[st.Expression],
    *ops: st.BinaryOpType,
) -> parsy.Parser[st.Expression]:
    @parsy.generate
    def parser() -> Generator[Any, Any, st.Expression]:
        lhs = yield from parse(lhs_parser)
        rest = yield from parse(parsy.seq(enum(*ops), rhs_parser).optional())

        if rest is None:
            return lhs

        op, rhs = rest
        return st.BinaryOp(op, lhs, rhs)

    return parser


@parsy.generate
def _expression_parser_2() -> Generator[Any, Any, st.Expression]:
    """unary prefix"""

    unary_parser = parsy.seq(
        enum(st.UnaryOpType.MINUS, st.UnaryOpType.NOT), _expression_parser_2
    )
    expr_builder_parser = map(unary_parser, lambda op, expr: st.UnaryOp(op, expr))
    return (yield from parse(expr_builder_parser | _expression_parser_1))


@parsy.generate
def _expression_parser_3() -> Generator[Any, Any, st.Expression]:
    """multiplicative"""

    ops = [st.BinaryOpType.MULT, st.BinaryOpType.DIV, st.BinaryOpType.MOD]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_2, _expression_parser_3, *ops)
        )
    )


@parsy.generate
def _expression_parser_4() -> Generator[Any, Any, st.Expression]:
    """additive"""

    ops = [st.BinaryOpType.PLUS, st.BinaryOpType.MINUS]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_3, _expression_parser_4, *ops)
        )
    )


@parsy.generate
def _expression_parser_5() -> Generator[Any, Any, st.Expression]:
    """comparison"""

    ops = [
        st.BinaryOpType.EQ,
        st.BinaryOpType.NEQ,
        st.BinaryOpType.LE,
        st.BinaryOpType.GE,
        st.BinaryOpType.LEQ,
        st.BinaryOpType.GEQ,
    ]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_4, _expression_parser_5, *ops)
        )
    )


@parsy.generate
def _expression_parser_6() -> Generator[Any, Any, st.Expression]:
    """and"""

    ops = [st.BinaryOpType.AND, st.BinaryOpType.AND_THEN]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_5, _expression_parser_6, *ops)
        )
    )


@parsy.generate
def _expression_parser_7() -> Generator[Any, Any, st.Expression]:
    """xor"""

    ops = [st.BinaryOpType.XOR]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_6, _expression_parser_7, *ops)
        )
    )


@parsy.generate
def _expression_parser_8() -> Generator[Any, Any, st.Expression]:
    """or"""

    ops = [st.BinaryOpType.OR, st.BinaryOpType.OR_ELSE]
    return (
        yield from parse(
            _make_binary_ops(_expression_parser_7, _expression_parser_8, *ops)
        )
    )


@parsy.generate
def expression_parser() -> Generator[Any, Any, st.Expression]:
    expression = yield from parse(_expression_parser_8)
    return expression


@parsy.generate
def variable_definition_parser() -> (
    Generator[Any, Any, st.Attributed[st.VariableDefinition]]
):
    default_value_parser = (token(":=") >> expression_parser).optional()

    attributes = yield from parse(attributes_parser)
    name = yield from parse(identifier_parser)
    linkage = yield from parse(variable_linkage_parser)
    yield token(":")
    type = yield from parse(type_parser)
    default_value = yield from parse(default_value_parser)
    yield token(";")

    return st.Attributed(
        attributes, st.VariableDefinition(name, linkage(type), default_value)
    )


def _make_var_block_kind_parser(kind: st.VarBlockType) -> parsy.Parser[st.VarBlockType]:
    return token(kind.name).map(lambda _: kind)


@parsy.generate
def var_block_parser() -> Generator[Any, Any, st.VarBlock]:
    kind_var_input_parser = _make_var_block_kind_parser(st.VarBlockType.VAR_INPUT)
    kind_var_output_parser = _make_var_block_kind_parser(st.VarBlockType.VAR_OUTPUT)
    kind_var_in_out_parser = _make_var_block_kind_parser(st.VarBlockType.VAR_IN_OUT)
    kind_var_inst_parser = _make_var_block_kind_parser(st.VarBlockType.VAR_INST)
    kind_var_parser = _make_var_block_kind_parser(st.VarBlockType.VAR)
    kind_parser = (
        kind_var_input_parser
        | kind_var_output_parser
        | kind_var_in_out_parser
        | kind_var_inst_parser
        | kind_var_parser
    )
    end_parser = token("END_VAR")

    comments = yield from parse(comment_parser.many())
    kind = yield from parse(kind_parser)
    constant = yield from parse(constant_parser)
    members = yield from parse(variable_definition_parser.many())
    yield end_parser

    return st.VarBlock(kind, comments, members, constant)


@parsy.generate
def struct_parser() -> Generator[Any, Any, Callable[[st.Identifier], st.Struct]]:
    members_parser = variable_definition_parser.many()

    yield token("STRUCT")
    members = yield from parse(members_parser)
    yield token("END_STRUCT")

    return lambda name: st.Struct(name, members)


@parsy.generate
def typedef_parser() -> Generator[Any, Any, st.Attributed[st.Enum | st.Struct]]:
    attributes = yield from parse(attributes_parser)
    yield token("TYPE")
    name = yield from parse(identifier_parser)
    yield token(":")
    builder = yield from parse(enum_parser | struct_parser)
    yield token("END_TYPE")

    return st.Attributed(attributes, builder(name))


@parsy.generate
def globals_parser() -> (
    Generator[Any, Any, Callable[[st.Identifier], st.Attributed[st.Globals]]]
):
    members_parser = variable_definition_parser.many()

    attributes = yield from parse(attributes_parser)
    yield token("VAR_GLOBAL")
    constant = yield from parse(constant_parser)
    members = yield from parse(members_parser)
    yield token("END_VAR")

    return lambda name: st.Attributed(
        attributes,
        st.Globals(name, members, constant),
    )


@parsy.generate
def assign_parser() -> Generator[Any, Any, st.Statement]:
    ref_parser = token(":=").map(lambda _: False) | token("REF=").map(lambda _: True)

    lhs = yield from parse(expression_parser)
    rest = yield from parse(parsy.seq(ref_parser, expression_parser).optional())
    yield token(";")

    if rest is None:
        return lhs

    ref, rhs = rest
    return st.Assign(lhs, rhs, ref)


@parsy.generate
def if_parser() -> Generator[Any, Any, st.If]:
    yield token("IF")
    condition = yield from parse(expression_parser)
    branch_parser = statement_parser.many()
    true = yield from parse(token("THEN") >> branch_parser)

    else_if_parser = parsy.string("ELS", transform=str.upper) >> if_parser
    else_if = yield from parse(else_if_parser.optional())
    if else_if is not None:
        return st.If(condition, true, [else_if])

    false = yield from parse((token("ELSE") >> branch_parser).optional([]))
    yield token("END_IF")
    return st.If(condition, true, false)


@parsy.generate
def case_parser() -> Generator[Any, Any, st.Case]:
    yield token("CASE")
    switch = yield from parse(expression_parser)
    yield token("OF")
    case_parser = parsy.seq(expression_parser << token(":"), statement_parser.many())
    cases = yield from parse(case_parser.many())
    default_parser = token("ELSE") >> statement_parser.many()
    default = yield from parse(default_parser.optional([]))
    yield token("END_CASE")
    return st.Case(switch, cases, default)


@parsy.generate
def keyword_parser() -> Generator[Any, Any, st.Statement]:
    return_parser = token("RETURN").map(lambda _: st.Return())
    keyword_parser = return_parser

    return (yield from parse(keyword_parser << token(";")))


@parsy.generate
def statement_parser() -> Generator[Any, Any, st.Statement]:
    parser = comment_parser | if_parser | case_parser | keyword_parser

    statement = yield from parse(parser | assign_parser)
    if (whitespace_lines.value) > 1:
        statement = st.Whitespaced(statement)
    return statement


@parsy.generate
def program_parser() -> Generator[Any, Any, st.Program]:
    attributes = yield from parse(attributes_parser)
    yield token("PROGRAM")
    name = yield from parse(identifier_parser)
    var_blocks = yield from parse(var_block_parser.many())
    components = yield from parse(components_parser.many())
    yield token("END_PROGRAM")
    statements = [item for item in components if isinstance(item, st.Statement)]
    properties = [item for item in components if isinstance(item, st.Property)]
    methods = [item for item in components if isinstance(item, st.Method)]

    return st.Program(
        st.Attributed(attributes, name), var_blocks, statements, properties, methods
    )


access_specifier_parser = enum(*st.AccessSpecifier).optional(st.AccessSpecifier.PUBLIC)


@parsy.generate
def method_parser() -> Generator[Any, Any, st.Method]:
    attributes = yield from parse(attributes_parser)
    yield token("METHOD")
    access = yield from parse(access_specifier_parser)
    name = yield from parse(identifier_parser)
    type = yield from parse((token(":") >> type_parser).optional())
    var_blocks = yield from parse(var_block_parser.many())
    statements = yield from parse(statement_parser.many())
    yield token("END_METHOD")
    return st.Method(
        st.Attributed(attributes, name), access, var_blocks, type, statements
    )


@parsy.generate
def function_parser() -> Generator[Any, Any, st.Function]:
    attributes = yield from parse(attributes_parser)
    yield token("FUNCTION")
    name = yield from parse(identifier_parser)
    type = yield from parse((token(":") >> type_parser).optional())
    var_blocks = yield from parse(var_block_parser.many())
    statements = yield from parse(statement_parser.many())
    yield token("END_FUNCTION")
    return st.Function(st.Attributed(attributes, name), var_blocks, type, statements)


@parsy.generate
def property_parser() -> Generator[Any, Any, st.Property]:
    attributes = yield from parse(attributes_parser)
    yield token("PROPERTY")
    access = yield from parse(access_specifier_parser)
    name = yield from parse(identifier_parser)
    type = yield from parse((token(":") >> type_parser))
    get_set_parser = (
        parsy.seq(property_get_parser, property_set_parser.optional())
        | parsy.seq(property_set_parser, property_get_parser.optional()).map(
            lambda set_get: (set_get[1], set_get[0])
        )
    ).optional((None, None))
    get, set = yield from parse(get_set_parser)
    yield token("END_PROPERTY")

    return st.Property(st.Attributed(attributes, name), access, type, get=get, set=set)


@parsy.generate
def property_set_parser() -> Generator[Any, Any, st.Attributed[st.PropertyMethod]]:
    attributes = yield from parse(attributes_parser)
    yield token("SET")
    var_blocks = yield from parse(var_block_parser.many())
    statements = yield from parse(statement_parser.many())
    yield token("END_SET")

    return st.Attributed(attributes, st.PropertyMethod(var_blocks, statements))


@parsy.generate
def property_get_parser() -> Generator[Any, Any, st.Attributed[st.PropertyMethod]]:
    attributes = yield from parse(attributes_parser)
    yield token("GET")
    var_blocks = yield from parse(var_block_parser.many())
    statements = yield from parse(statement_parser.many())
    yield token("END_GET")

    return st.Attributed(attributes, st.PropertyMethod(var_blocks, statements))


components_parser = statement_parser | method_parser | property_parser


@parsy.generate
def function_block_parser() -> Generator[Any, Any, st.FunctionBlock]:
    attributes = yield from parse(attributes_parser)
    yield token("FUNCTION_BLOCK")
    name = yield from parse(identifier_parser)
    extends = yield from parse((token("EXTENDS") >> identifier_parser).optional())
    implements = yield from parse(
        (token("IMPLEMENTS") >> identifier_parser.sep_by(token(","), min=1)).optional(
            []
        )
    )
    var_blocks = yield from parse(var_block_parser.many())
    components = yield from parse(components_parser.many())
    yield token("END_FUNCTION_BLOCK")
    statements = [item for item in components if isinstance(item, st.Statement)]
    properties = [item for item in components if isinstance(item, st.Property)]
    methods = [item for item in components if isinstance(item, st.Method)]
    return st.FunctionBlock(
        st.Attributed(attributes, name),
        extends,
        implements,
        var_blocks,
        statements,
        properties,
        methods,
    )


@parsy.generate
def interface_parser() -> Generator[Any, Any, st.Interface]:
    attributes = yield from parse(attributes_parser)
    yield token("INTERFACE")
    name = yield from parse(identifier_parser)
    extends = yield from parse(
        (token("EXTENDS") >> identifier_parser.sep_by(token(","), min=1)).optional([])
    )
    components_parser = property_parser | method_parser
    components = yield from parse(components_parser.many())
    properties = [
        st.PropertySignature(
            item.name,
            item.type,
            has_get=item.get is not None,
            has_set=item.set is not None,
        )
        for item in components
        if isinstance(item, st.Property)
    ]
    methods = [
        st.MethodSignature(item.name, item.access, item.vars, item.type)
        for item in components
        if isinstance(item, st.Method)
    ]
    yield token("END_INTERFACE")
    return st.Interface(st.Attributed(attributes, name), extends, properties, methods)


pou_parser = program_parser | function_block_parser


@parsy.generate
def structured_text_parser() -> Generator[Any, Any, Callable[[Path], list[st.ASTNode]]]:
    def path_to_name(path: Path) -> st.Identifier:
        name = path.name.split(".")[0]
        return st.Identifier(name)

    def globals_builder(
        builder: Callable[[st.Identifier], st.ASTNode],
    ) -> Callable[[Path], st.ASTNode]:
        return lambda path: builder(path_to_name(path))

    def ignore_path(node: st.ASTNode) -> Callable[[Path], st.ASTNode]:
        return lambda _: node

    node_parser = (
        program_parser
        | function_block_parser
        | function_parser
        | typedef_parser
        | interface_parser
    ).map(ignore_path)
    gvl_parser = globals_parser.map(globals_builder)

    yield whitespace_parser
    node_parser = gvl_parser | node_parser
    builders = yield from parse(node_parser.at_least(1))
    return lambda path: [builder(path) for builder in builders]
