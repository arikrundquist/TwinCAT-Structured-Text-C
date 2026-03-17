from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import StrEnum
from typing import Generic, TypeAlias, TypeVar, override


class AccessSpecifier(StrEnum):
    PUBLIC = "PUBLIC"
    PRIVATE = "PRIVATE"
    PROTECTED = "PROTECTED"


class VarBlockType(StrEnum):
    VAR = "VAR"
    VAR_INPUT = "VAR_INPUT"
    VAR_OUTPUT = "VAR_OUTPUT"
    VAR_IN_OUT = "VAR_IN_OUT"
    VAR_INST = "VAR_INST"


class UnaryOpType(StrEnum):
    MINUS = "-"
    NOT = "NOT "


class BinaryOpType(StrEnum):
    MULT = "*"
    DIV = "/"
    MOD = "MOD "
    PLUS = "+"
    MINUS = "-"
    EQ = "="
    NEQ = "<>"
    GE = ">"
    LE = "<"
    GEQ = ">="
    LEQ = "<="
    AND = "AND"
    AND_THEN = "AND_THEN"
    XOR = "XOR"
    OR = "OR"
    OR_ELSE = "OR_ELSE"


@dataclass
class ASTNode(ABC):
    @abstractmethod
    def accept(self, visitor: Visitor[_T]) -> _T:
        pass


_T = TypeVar("_T")
_Node = TypeVar("_Node", bound=ASTNode)


@dataclass
class Identifier(ASTNode):
    name: str

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_identifier(self)

    def __hash__(self) -> int:
        return hash(self.name)


@dataclass
class Integer(ASTNode):
    value: int
    base: int

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_integer(self)


@dataclass
class String(ASTNode):
    value: str

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_string(self)


@dataclass
class Time(ASTNode):
    millis: int

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_time(self)


@dataclass
class Parenthesized(ASTNode):
    expression: Expression

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_parenthesized(self)


@dataclass
class Attributed(Generic[_Node], ASTNode):
    attributes: list[Attribute | Comment]
    value: _Node

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_attributed(self)

    def separate(self) -> tuple[list[Comment], list[Attribute]]:
        comments = list[Comment]()
        attributes = list[Attribute]()
        for item in self.attributes:
            if isinstance(item, Comment):
                comments.append(item)
                continue

            attributes.append(item)

        return comments, attributes


@dataclass
class Attribute(ASTNode):
    name: str

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_attribute(self)


@dataclass
class AttributeEq(Attribute):
    value: str

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_attribute_value(self)


@dataclass
class Comment(ASTNode):
    comment: str

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_comment(self)


@dataclass
class EnumElement(ASTNode):
    name: Identifier
    value: int | None

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_enum_element(self)


@dataclass
class Enum(ASTNode):
    name: Identifier
    type: str | None
    items: list[EnumElement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_enum(self)


@dataclass
class Pointer(ASTNode):
    type: Type

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_pointer(self)


@dataclass
class Reference(ASTNode):
    type: Type

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_reference(self)


@dataclass
class DynamicArray(ASTNode):
    type: Type

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_dynamic_array(self)


@dataclass
class BoundedArray(ASTNode):
    type: Type
    low: Integer
    high: Integer

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_bounded_array(self)


Array: TypeAlias = DynamicArray | BoundedArray


@dataclass
class Struct(ASTNode):
    name: Identifier
    members: list[Attributed[VariableDefinition]]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_struct(self)


@dataclass
class Globals(ASTNode):
    name: Identifier
    members: list[Attributed[VariableDefinition]]
    constant: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_globals(self)


@dataclass
class VariableDefinition(ASTNode):
    name: Identifier
    type: Linked
    default: Expression | None

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_variable_definition(self)


@dataclass
class VarBlock(ASTNode):
    kind: VarBlockType
    comments: list[Comment]
    members: list[Attributed[VariableDefinition]]
    constant: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_variable_block(self)


@dataclass
class LinkedIn(ASTNode):
    type: Type

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_linked_in(self)


@dataclass
class LinkedOut(ASTNode):
    type: Type

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_linked_out(self)


@dataclass
class Record(ASTNode):
    expression: Expression
    name: Identifier
    ptr: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_record(self)


@dataclass
class Index(ASTNode):
    expression: Expression
    index: Expression

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_index(self)


@dataclass
class Kwarg(ASTNode):
    name: Identifier
    value: Expression | None
    out: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_kwarg(self)


@dataclass
class FuncCall(ASTNode):
    expression: Expression
    args: list[Expression]
    kwargs: list[Kwarg]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_function_call(self)


@dataclass
class Initializer(ASTNode):
    initializers: list[tuple[Identifier, Expression]]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_initializer(self)


@dataclass
class UnaryOp(ASTNode):
    operator: UnaryOpType
    expression: Expression

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_unary_operator(self)


@dataclass
class BinaryOp(ASTNode):
    operator: BinaryOpType
    lhs: Expression
    rhs: Expression

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_binary_operator(self)


@dataclass
class If(ASTNode):
    condition: Expression
    true: list[Statement]
    false: list[Statement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_if(self)


@dataclass
class Case(ASTNode):
    switch: Expression
    cases: list[tuple[Expression, list[Statement]]]
    default: list[Statement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_case(self)


@dataclass
class Assign(ASTNode):
    lhs: Expression
    rhs: Expression
    ref: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_assign(self)


@dataclass
class Return(ASTNode):
    pass

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_return(self)


@dataclass
class Interface(ASTNode):
    name: Attributed[Identifier]
    extends: list[Identifier]
    properties: list[PropertySignature]
    methods: list[MethodSignature]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_interface(self)


@dataclass
class FunctionBlock(ASTNode):
    name: Attributed[Identifier]
    extends: Identifier | None
    implements: list[Identifier]
    vars: list[VarBlock]
    statements: list[Statement]
    properties: list[Property]
    methods: list[Method]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_function_block(self)


@dataclass
class Program(ASTNode):
    name: Attributed[Identifier]
    vars: list[VarBlock]
    statements: list[Statement]
    properties: list[Property]
    methods: list[Method]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_program(self)


@dataclass
class Function(ASTNode):
    name: Attributed[Identifier]
    vars: list[VarBlock]
    type: Type | None
    statements: list[Statement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_function(self)


@dataclass
class MethodSignature(ASTNode):
    name: Attributed[Identifier]
    access: AccessSpecifier
    vars: list[VarBlock]
    type: Type | None

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_method_signature(self)


@dataclass
class Method(MethodSignature):
    statements: list[Statement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_method(self)


@dataclass
class PropertySignature(ASTNode):
    name: Attributed[Identifier]
    type: Type
    has_get: bool
    has_set: bool

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_property_signature(self)


@dataclass
class PropertyMethod(ASTNode):
    vars: list[VarBlock]
    statements: list[Statement]

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_property_method(self)


@dataclass
class Property(ASTNode):
    name: Attributed[Identifier]
    access: AccessSpecifier
    type: Type
    get: Attributed[PropertyMethod] | None
    set: Attributed[PropertyMethod] | None

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_property(self)


@dataclass
class Whitespaced(ASTNode):
    statement: Statement

    @override
    def accept(self, visitor: Visitor[_T]) -> _T:
        return visitor.visit_whitespaced(self)


Expression: TypeAlias = (
    Integer
    | Time
    | String
    | Identifier
    | Initializer
    | UnaryOp
    | BinaryOp
    | FuncCall
    | Record
    | Index
)
Statement: TypeAlias = Comment | Expression | If | Case | Assign | Return | Whitespaced

Type: TypeAlias = Reference | Pointer | Array | Identifier
Linked: TypeAlias = Type | LinkedIn | LinkedOut


class Visitor(Generic[_T], ABC):
    def visit(self, node: ASTNode, /) -> _T:
        return node.accept(self)

    @abstractmethod
    def visit_whitespaced(self, whitespaced: Whitespaced, /) -> _T:
        pass

    @abstractmethod
    def visit_identifier(self, identifier: Identifier, /) -> _T:
        pass

    @abstractmethod
    def visit_integer(self, integer: Integer, /) -> _T:
        pass

    @abstractmethod
    def visit_string(self, string: String, /) -> _T:
        pass

    @abstractmethod
    def visit_time(self, time: Time, /) -> _T:
        pass

    @abstractmethod
    def visit_parenthesized(self, parenthesized: Parenthesized, /) -> _T:
        pass

    @abstractmethod
    def visit_attributed(self, attributed: Attributed[_Node], /) -> _T:
        pass

    @abstractmethod
    def visit_attribute(self, attribute: Attribute, /) -> _T:
        pass

    @abstractmethod
    def visit_attribute_value(self, attribute: AttributeEq, /) -> _T:
        pass

    @abstractmethod
    def visit_comment(self, comment: Comment, /) -> _T:
        pass

    @abstractmethod
    def visit_enum_element(self, enum: EnumElement, /) -> _T:
        pass

    @abstractmethod
    def visit_enum(self, enum: Enum, /) -> _T:
        pass

    @abstractmethod
    def visit_pointer(self, pointer: Pointer, /) -> _T:
        pass

    @abstractmethod
    def visit_reference(self, reference: Reference, /) -> _T:
        pass

    @abstractmethod
    def visit_dynamic_array(self, array: DynamicArray, /) -> _T:
        pass

    @abstractmethod
    def visit_bounded_array(self, array: BoundedArray, /) -> _T:
        pass

    @abstractmethod
    def visit_struct(self, struct: Struct, /) -> _T:
        pass

    @abstractmethod
    def visit_globals(self, globals: Globals, /) -> _T:
        pass

    @abstractmethod
    def visit_variable_definition(self, definition: VariableDefinition, /) -> _T:
        pass

    @abstractmethod
    def visit_variable_block(self, block: VarBlock, /) -> _T:
        pass

    @abstractmethod
    def visit_linked_in(self, linked: LinkedIn, /) -> _T:
        pass

    @abstractmethod
    def visit_linked_out(self, linked: LinkedOut, /) -> _T:
        pass

    @abstractmethod
    def visit_record(self, record: Record, /) -> _T:
        pass

    @abstractmethod
    def visit_index(self, index: Index, /) -> _T:
        pass

    @abstractmethod
    def visit_kwarg(self, kwarg: Kwarg, /) -> _T:
        pass

    @abstractmethod
    def visit_function_call(self, call: FuncCall, /) -> _T:
        pass

    @abstractmethod
    def visit_initializer(self, initializer: Initializer, /) -> _T:
        pass

    @abstractmethod
    def visit_unary_operator(self, op: UnaryOp, /) -> _T:
        pass

    @abstractmethod
    def visit_binary_operator(self, op: BinaryOp, /) -> _T:
        pass

    @abstractmethod
    def visit_if(self, fi: If, /) -> _T:
        pass

    @abstractmethod
    def visit_case(self, case: Case, /) -> _T:
        pass

    @abstractmethod
    def visit_assign(self, assign: Assign, /) -> _T:
        pass

    @abstractmethod
    def visit_return(self, ret: Return, /) -> _T:
        pass

    @abstractmethod
    def visit_interface(self, interface: Interface, /) -> _T:
        pass

    @abstractmethod
    def visit_function_block(self, fb: FunctionBlock, /) -> _T:
        pass

    @abstractmethod
    def visit_program(self, program: Program, /) -> _T:
        pass

    @abstractmethod
    def visit_function(self, function: Function, /) -> _T:
        pass

    @abstractmethod
    def visit_method_signature(self, signature: MethodSignature, /) -> _T:
        pass

    @abstractmethod
    def visit_method(self, method: Method, /) -> _T:
        pass

    @abstractmethod
    def visit_property_signature(self, signature: PropertySignature, /) -> _T:
        pass

    @abstractmethod
    def visit_property_method(self, method: PropertyMethod, /) -> _T:
        pass

    @abstractmethod
    def visit_property(self, property: Property, /) -> _T:
        pass
