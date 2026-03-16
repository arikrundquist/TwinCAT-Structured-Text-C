from enum import Enum, auto
from typing import Iterator, TypeVar, override

from tcstc.models import structured_text as st

_T = TypeVar("_T", bound=st.ASTNode)


def format(node: st.ASTNode, *, indent: str = "  ", level: int = 0) -> str:
    return _FormatterVisitor().format(node, indent=indent, level=level)


class _FormatSection(Enum):
    VAR = auto()
    STATEMENT = auto()
    PROPERTY = auto()
    METHOD = auto()


class _FormatterVisitor(st.Visitor[str]):
    def __init__(self) -> None:
        self._section = _FormatSection.VAR
        self._prev_statement: st.Statement | None = None

    def format(self, node: st.ASTNode, *, indent: str = "  ", level: int = 0) -> str:
        return node.accept(self)

    def indent(self, string: str) -> str:
        return f"\t{string}".replace("\n", "\n\t")

    def section(self, section: _FormatSection) -> Iterator[str]:
        if self._section == section:
            return

        self._section = section
        yield ""

    @override
    def visit_whitespaced(self, whitespaced: st.Whitespaced) -> str:
        return f"{self.visit_statement(whitespaced.statement)}\n"

    def visit_statement(self, statement: st.Statement) -> str:
        self._prev_statement = statement
        match statement:
            case st.Comment():
                return f"{self.visit(statement)}"

            case st.If() | st.Comment() | st.Case() | st.Whitespaced():
                return self.visit(statement)

            case _:
                return f"{self.visit(statement)};"

    @override
    def visit_identifier(self, identifier: st.Identifier, /) -> str:
        return identifier.name

    @override
    def visit_integer(self, integer: st.Integer, /) -> str:
        match base := integer.base:
            case 2:
                return f"2#{integer.value:b}"

            case 8:
                return f"8#{integer.value:o}"

            case 16:
                return f"16#{integer.value:02X}"

            case _:
                assert base == 10
                return f"{integer.value}"

    @override
    def visit_string(self, string: st.String, /) -> str:
        return f"'{string.value}'"

    @override
    def visit_time(self, time: st.Time, /) -> str:
        def generate_components() -> Iterator[str]:
            ref = st.Time(time.millis)

            for unit, divisor in [
                ("ms", 1000),
                ("s", 60),
                ("m", 60),
                ("h", 24),
                ("d", ref.millis),
            ]:
                value = ref.millis % divisor
                ref.millis = ref.millis // divisor
                if value:
                    yield f"{value}{unit}"

        time_string = "".join(generate_components()) or "0ms"
        return f"T#{time_string}"

    @override
    def visit_parenthesized(self, parenthesized: st.Parenthesized, /) -> str:
        return f"({self.visit(parenthesized.expression)})"

    @override
    def visit_attributed(self, attributed: st.Attributed[_T], /) -> str:
        def generate_components() -> Iterator[str]:
            comments, attributes = attributed.separate()
            if comments:
                yield from map(self.visit, comments)
            yield from map(self.visit, attributes)
            yield self.visit(attributed.value)

        return "\n".join(generate_components())

    @override
    def visit_attribute(self, attribute: st.Attribute, /) -> str:
        return f"{{attribute '{attribute.name}'}}"

    @override
    def visit_attribute_value(self, attribute: st.AttributeEq, /) -> str:
        return f"{{attribute '{attribute.name}' := '{attribute.value}'}}"

    @override
    def visit_comment(self, comment: st.Comment, /) -> str:
        return comment.comment

    @override
    def visit_enum_element(self, enum: st.EnumElement, /) -> str:
        name = self.visit(enum.name)
        return f"{name}" if enum.value is None else f"{name} := {enum.value}"

    @override
    def visit_enum(self, enum: st.Enum, /) -> str:
        type = f" {enum.type}" if enum.type else ""

        elements = ",\n".join(
            self.indent(self.visit(element)) for element in enum.items
        )

        return f"""TYPE {self.visit(enum.name)} :
(
{elements}
){type};
END_TYPE
"""

    @override
    def visit_pointer(self, pointer: st.Pointer, /) -> str:
        return f"POINTER TO {self.visit(pointer.type)}"

    @override
    def visit_reference(self, reference: st.Reference, /) -> str:
        return f"REFERENCE TO {self.visit(reference.type)}"

    @override
    def visit_dynamic_array(self, array: st.DynamicArray, /) -> str:
        return f"ARRAY[*] OF {self.visit(array.type)}"

    @override
    def visit_bounded_array(self, array: st.BoundedArray, /) -> str:
        return f"ARRAY[{self.visit(array.low)}..{self.visit(array.high)}] OF {self.visit(array.type)}"

    @override
    def visit_struct(self, struct: st.Struct, /) -> str:
        self._set_padding(struct.members)
        elements = "\n".join(
            self.indent(self.visit(element)) for element in struct.members
        )

        return f"""TYPE {self.visit(struct.name)} :
STRUCT
{elements}
END_STRUCT
END_TYPE
"""

    @override
    def visit_globals(self, globals: st.Globals, /) -> str:
        constant = " CONSTANT" if globals.constant else ""

        self._set_padding(globals.members)
        elements = "\n".join(
            self.indent(self.visit(element)) for element in globals.members
        )

        return f"""VAR_GLOBAL{constant}
{elements}
END_VAR
"""

    def _set_padding(
        self, definitions: list[st.Attributed[st.VariableDefinition]]
    ) -> None:
        self._padding = max(
            (len(self.visit(definition.value.name)) for definition in definitions),
            default=0,
        )
        self._linkage_padding = max(
            (len(self._get_linkage(definition.value)) for definition in definitions),
            default=0,
        )

    def _get_linkage(self, definition: st.VariableDefinition) -> str:
        match definition.type:
            case st.LinkedIn():
                return " AT %I* "
            case st.LinkedOut():
                return " AT %Q* "
            case _:
                return ""

    @override
    def visit_variable_definition(self, definition: st.VariableDefinition, /) -> str:
        default = f" := {self.visit(definition.default)}" if definition.default else ""
        name = self.visit(definition.name).ljust(self._padding)
        linkage = self._get_linkage(definition).rjust(self._linkage_padding)
        decl = f"{name}\t{linkage}"
        return f"{decl}: {self.visit(definition.type)}{default};"

    @override
    def visit_variable_block(self, block: st.VarBlock, /) -> str:
        def generate_components() -> Iterator[str]:
            if block.comments:
                yield ""
            yield from map(self.visit, block.comments)
            constant = " CONSTANT" if block.constant else ""
            yield f"{block.kind.value}{constant}"
            self._set_padding(block.members)
            for member in block.members:
                yield self.indent(self.visit(member))
            yield "END_VAR"

        return "\n".join(generate_components())

    @override
    def visit_linked_in(self, linked: st.LinkedIn, /) -> str:
        return self.visit(linked.type)

    @override
    def visit_linked_out(self, linked: st.LinkedOut, /) -> str:
        return self.visit(linked.type)

    @override
    def visit_record(self, record: st.Record, /) -> str:
        dot = "^." if record.ptr else "."
        return f"{self.visit(record.expression)}{dot}{self.visit(record.name)}"

    @override
    def visit_index(self, index: st.Index, /) -> str:
        return f"{self.visit(index.expression)}[{self.visit(index.index)}]"

    @override
    def visit_kwarg(self, kwarg: st.Kwarg) -> str:
        arrow = "=>" if kwarg.out else ":="
        name = self.visit(kwarg.name)
        expr = self.visit(kwarg.value) if kwarg.value else ""
        return f"{name} {arrow} {expr}"

    @override
    def visit_function_call(self, call: st.FuncCall, /) -> str:
        expression = self.visit(call.expression)
        if not call.kwargs:
            return f"{expression}({", ".join(map(self.visit, call.args))})"

        if len(call.kwargs) == 1:
            (kwarg,) = call.kwargs
            return f"{expression}({self.visit(kwarg)})"

        def generate_components() -> Iterator[str]:
            yield f"{expression}("

            def generate_args() -> Iterator[str]:
                for arg in call.args:
                    yield self.visit(arg)
                for kwarg in call.kwargs:
                    yield self.visit(kwarg)

            yield self.indent(",\n".join(generate_args()))
            yield ")"

        return "\n".join(generate_components())

    @override
    def visit_initializer(self, initializer: st.Initializer, /) -> str:
        initializers = ", ".join(
            f"{self.visit(name)} := {self.visit(value)}"
            for (name, value) in initializer.initializers
        )
        return f"({initializers})"

    @override
    def visit_unary_operator(self, op: st.UnaryOp, /) -> str:
        return f"{op.operator.value}{self.visit(op.expression)}"

    @override
    def visit_binary_operator(self, op: st.BinaryOp, /) -> str:
        return f"{self.visit(op.lhs)} {op.operator.value} {self.visit(op.rhs)}"

    @override
    def visit_if(self, fi: st.If, /) -> str:
        def generate_components() -> Iterator[str]:
            yield f"IF {self.visit(fi.condition)} THEN"
            self._prev_statement = None
            for statement in fi.true:
                yield self.indent(self.visit_statement(statement))

            false = tuple(fi.false)
            if len(false) == 1:
                (elsif,) = false
                if isinstance(elsif, st.If):
                    yield f"ELS{self.visit_statement(elsif)}"
                    return

            self._prev_statement = None
            for statement in fi.false:
                yield self.indent(self.visit_statement(statement))
            yield "END_IF"

        return "\n".join(generate_components())

    @override
    def visit_case(self, case: st.Case, /) -> str:
        def generate_components() -> Iterator[str]:
            yield f"CASE {self.visit(case.switch)} OF"
            for expr, statements in case.cases:
                yield self.indent(f"{self.visit(expr)}:")
                for statement in statements:
                    yield self.indent(self.indent(self.visit_statement(statement)))
            if case.default:
                yield self.indent("ELSE")
                for statement in case.default:
                    yield self.indent(self.indent(self.visit_statement(statement)))
            yield "END_CASE"

        return "\n".join(generate_components())

    @override
    def visit_assign(self, assign: st.Assign, /) -> str:
        equals = "REF=" if assign.ref else ":="
        return f"{self.visit(assign.lhs)} {equals} {self.visit(assign.rhs)}"

    @override
    def visit_return(self, ret: st.Return, /) -> str:
        return "RETURN"

    @override
    def visit_interface(self, interface: st.Interface, /) -> str:
        def generate_components() -> Iterator[str]:
            extends = (
                (
                    f" EXTENDS {", ".join(self.visit(item) for item in interface.extends)}"
                )
                if interface.extends
                else ""
            )
            yield f"INTERFACE {self.visit(interface.name)}{extends}"
            for property in interface.properties:
                yield self.indent(self.visit(property))
            for method in interface.methods:
                yield self.indent(self.visit(method))
            yield "END_INTERFACE\n"

        return "\n".join(generate_components())

    @override
    def visit_function_block(self, fb: st.FunctionBlock, /) -> str:
        def generate_components() -> Iterator[str]:
            extends = f" EXTENDS {self.visit(fb.extends)}" if fb.extends else ""
            implements = (
                f" IMPLEMENTS {", ".join(self.visit(item) for item in fb.implements)}"
                if fb.implements
                else ""
            )
            yield f"FUNCTION_BLOCK {self.visit(fb.name)}{extends}{implements}"
            self._section = _FormatSection.VAR
            for block in fb.vars:
                yield self.indent(self.visit(block))
            self._prev_statement = None
            for statement in fb.statements:
                yield from self.section(_FormatSection.STATEMENT)
                yield self.indent(self.visit_statement(statement))
            for property in fb.properties:
                yield from self.section(_FormatSection.PROPERTY)
                yield self.indent(self.visit(property))
            for method in fb.methods:
                yield from self.section(_FormatSection.METHOD)
                yield self.indent(self.visit(method))
            yield "END_FUNCTION_BLOCK\n"

        return "\n".join(generate_components())

    @override
    def visit_program(self, program: st.Program, /) -> str:
        def generate_components() -> Iterator[str]:
            yield f"PROGRAM {self.visit(program.name)}"
            self._section = _FormatSection.VAR
            for block in program.vars:
                yield self.indent(self.visit(block))
            self._prev_statement = None
            for statement in program.statements:
                yield from self.section(_FormatSection.STATEMENT)
                yield self.indent(self.visit_statement(statement))
            for property in program.properties:
                yield from self.section(_FormatSection.PROPERTY)
                yield self.indent(self.visit(property))
            for method in program.methods:
                yield from self.section(_FormatSection.METHOD)
                yield self.indent(self.visit(method))
            yield "END_PROGRAM\n"

        return "\n".join(generate_components())

    @override
    def visit_function(self, function: st.Function, /) -> str:
        def generate_components() -> Iterator[str]:
            yield f"FUNCTION {self.visit(function.name)}"
            self._section = _FormatSection.VAR
            for block in function.vars:
                yield self.indent(self.visit(block))
            self._prev_statement = None
            for statement in function.statements:
                yield from self.section(_FormatSection.STATEMENT)
                yield self.indent(self.visit_statement(statement))
            yield "END_FUNCTION\n"

        return "\n".join(generate_components())

    @override
    def visit_method_signature(self, signature: st.MethodSignature, /) -> str:
        def generate_components() -> Iterator[str]:
            access = (
                ""
                if signature.access == st.AccessSpecifier.PUBLIC
                else f" {signature.access.value}"
            )
            type = f" : {self.visit(signature.type)}" if signature.type else ""
            yield f"METHOD{access} {self.visit(signature.name)}{type}"
            for block in signature.vars:
                yield self.indent(self.visit(block))
            yield "END_METHOD\n"

        return "\n".join(generate_components())

    @override
    def visit_method(self, method: st.Method, /) -> str:
        def generate_components() -> Iterator[str]:
            access = (
                ""
                if method.access == st.AccessSpecifier.PUBLIC
                else f" {method.access.value}"
            )
            type = f" : {self.visit(method.type)}" if method.type else ""
            yield f"METHOD{access} {self.visit(method.name)}{type}"
            for block in method.vars:
                yield self.indent(self.visit(block))
            if method.vars and method.statements:
                yield ""
            self._prev_statement = None
            for statement in method.statements:
                yield self.indent(self.visit_statement(statement))
            yield "END_METHOD\n"

        return "\n".join(generate_components())

    @override
    def visit_property_signature(self, signature: st.PropertySignature, /) -> str:
        def generate_components() -> Iterator[str]:
            yield f"PROPERTY {self.visit(signature.name)} : {self.visit(signature.type)}"
            if signature.has_get:
                yield self.indent("GET")
                yield self.indent("END_GET")
            if signature.has_set:
                yield self.indent("SET")
                yield self.indent("END_SET")
            yield "END_PROPERTY\n"

        return "\n".join(generate_components())

    @override
    def visit_property_method(self, method: st.PropertyMethod, /) -> str:
        def generate_components() -> Iterator[str]:
            for block in method.vars:
                yield self.indent(self.visit(block))
            if method.vars and method.statements:
                yield ""
            self._prev_statement = None
            for statement in method.statements:
                yield self.indent(self.visit_statement(statement))

        return "\n".join(generate_components())

    @override
    def visit_property(self, property: st.Property, /) -> str:
        def generate_components() -> Iterator[str]:
            yield from self.section(_FormatSection.PROPERTY)
            access = (
                ""
                if property.access == st.AccessSpecifier.PUBLIC
                else f" {property.access.value}"
            )
            yield f"PROPERTY{access} {self.visit(property.name)} : {self.visit(property.type)}"
            if property.get:
                yield self.indent("GET")
                yield self.indent(self.visit(property.get))
                yield self.indent("END_GET")
            if property.set:
                yield self.indent("SET")
                yield self.indent(self.visit(property.set))
                yield self.indent("END_SET")
            yield "END_PROPERTY\n"

        return "\n".join(generate_components())
