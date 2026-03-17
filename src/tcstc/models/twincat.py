from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator, Literal, ParamSpec, Sequence, final, override
from xml.etree import ElementTree as XML

from tcstc.models.structured_text.tokens import Keyword
from tcstc.parsers.structured_text.tokens import parser

_P = ParamSpec("_P")


@dataclass(kw_only=True)
class TwinCatObject(ABC):
    path: Path | None = None

    @staticmethod
    def object_types() -> Iterable[type[TwinCatObject]]:
        return [
            TwinCatGVL,
            TwinCatDUT,
            TwinCatIO,
            TwinCatPOU,
        ]

    @classmethod
    @abstractmethod
    def extension(cls) -> str:
        """the TwinCAT extension this type handles (e.g. `.TcGVL`)"""

    @abstractmethod
    def get_structured_text(self) -> str:
        """get the structured text in the object"""

    @classmethod
    @final
    def get_from_path(cls, path: Path) -> TwinCatObject:
        """load from TwinCAT xml"""
        object = cls.get_from_xml(XML.parse(path).getroot())
        object.path = path
        return object

    @classmethod
    @abstractmethod
    def get_from_xml(cls, xml: XML.Element) -> TwinCatObject:
        """load from TwinCAT xml"""

    # @classmethod
    # @abstractmethod
    # def get_empty_xml(cls) -> XML.Element:
    #     """get an empty xml document for this type"""

    # @abstractmethod
    # def set_into_xml(self, xml: XML.Element) -> None:
    #     """populate the xml document"""


def _find_tags(
    root: XML.Element, xpath: str, *, min: int | None = None, max: int | None = None
) -> Sequence[XML.Element]:
    elements = root.findall(xpath)
    count = len(elements)
    assert min is None or min <= count
    assert max is None or count <= max
    return elements


@dataclass
class TwinCatGVL(TwinCatObject):
    declaration: str

    @override
    @classmethod
    def extension(cls) -> str:
        return ".TcGVL"

    @override
    def get_structured_text(self) -> str:
        return self.declaration

    @override
    @classmethod
    def get_from_xml(cls, xml: XML.Element) -> TwinCatGVL:
        (declaration,) = _find_tags(xml, "GVL/Declaration", min=1, max=1)
        return TwinCatGVL(declaration.text or "")


@dataclass
class TwinCatDUT(TwinCatObject):
    declaration: str

    @override
    @classmethod
    def extension(cls) -> str:
        return ".TcDUT"

    @override
    def get_structured_text(self) -> str:
        return self.declaration

    @override
    @classmethod
    def get_from_xml(cls, xml: XML.Element) -> TwinCatDUT:
        (declaration,) = _find_tags(xml, "DUT/Declaration", min=1, max=1)
        return TwinCatDUT(declaration.text or "")


@dataclass
class TwinCatMethod:
    kind: str
    declaration: str
    implementation: str | None = None

    def get_structured_text(self) -> str:
        return f"""
{self.declaration}
{self.implementation or ""}
END_{self.kind}
""".strip()


@dataclass
class TwinCatProperty:
    declaration: str
    get: TwinCatMethod | None = None
    set: TwinCatMethod | None = None

    def _format_property_method(self, method: TwinCatMethod | None) -> str:
        if not method:
            return ""

        return f"""
{method.kind}
{method.get_structured_text()}
"""

    def get_structured_text(self) -> str:
        return f"""
{self.declaration}
{self._format_property_method(self.get)}
{self._format_property_method(self.set)}
END_PROPERTY
"""


def _get_method(
    xml: XML.Element, kind: Literal["GET", "SET", "METHOD"] = "METHOD"
) -> TwinCatMethod:
    (declaration,) = _find_tags(xml, "Declaration", min=1, max=1)
    method = TwinCatMethod(kind, declaration=declaration.text or "")
    for implementation in _find_tags(xml, "Implementation/ST", max=1):
        method.implementation = implementation.text or ""
    return method


def _get_property(xml: XML.Element) -> TwinCatProperty:
    (declaration,) = _find_tags(xml, "Declaration", min=1, max=1)
    property = TwinCatProperty(declaration.text or "")
    for getter in _find_tags(xml, "Get", max=1):
        property.get = _get_method(getter, "GET")
    for setter in _find_tags(xml, "Set", max=1):
        property.set = _get_method(setter, "SET")
    return property


def _iterate_methods(
    properties: Iterable[TwinCatProperty], methods: Iterable[TwinCatMethod]
) -> Iterator[TwinCatMethod]:
    for property in properties:
        if property.get:
            yield property.get

        if property.set:
            yield property.set

    yield from methods


def _check_for_implementations(
    expected: bool,
    properties: Iterable[TwinCatProperty],
    methods: Iterable[TwinCatMethod],
) -> None:
    for method in _iterate_methods(properties, methods):
        assert (method.implementation is not None) == expected


@dataclass
class TwinCatIO(TwinCatObject):
    declaration: str
    properties: list[TwinCatProperty]
    methods: list[TwinCatMethod]

    @override
    @classmethod
    def extension(cls) -> str:
        return ".TcIO"

    @override
    def get_structured_text(self) -> str:
        _check_for_implementations(False, self.properties, self.methods)
        properties = "\n\n".join(
            property.get_structured_text() for property in self.properties
        )
        methods = "\n\n".join(method.get_structured_text() for method in self.methods)
        return f"""
{self.declaration}
{properties}
{methods}
END_INTERFACE
"""

    @override
    @classmethod
    def get_from_xml(cls, xml: XML.Element) -> TwinCatIO:
        (declaration,) = _find_tags(xml, "Itf/Declaration", min=1, max=1)
        interface = TwinCatIO(declaration.text or "", [], [])
        for property in _find_tags(xml, "Itf/Property"):
            interface.properties.append(_get_property(property))
        for method in _find_tags(xml, "Itf/Method"):
            interface.methods.append(_get_method(method))
        return interface


@dataclass
class TwinCatPOU(TwinCatObject):
    kind: str
    declaration: str
    implementation: str
    properties: list[TwinCatProperty]
    methods: list[TwinCatMethod]

    @override
    @classmethod
    def extension(cls) -> str:
        return ".TcPOU"

    @override
    def get_structured_text(self) -> str:
        _check_for_implementations(True, self.properties, self.methods)
        properties = "\n\n".join(
            property.get_structured_text() for property in self.properties
        )
        methods = "\n\n".join(method.get_structured_text() for method in self.methods)
        return f"""
{self.declaration}
{self.implementation}
{properties}
{methods}
END_{self.kind}
"""

    @classmethod
    def _get_kind(cls, declaration: str) -> str:
        tokens = parser.parse(declaration)
        kinds = [Keyword.FUNCTION, Keyword.FUNCTION_BLOCK, Keyword.PROGRAM]
        for token in tokens:
            for kind in kinds:
                if token == kind:
                    return kind.value

        assert False

    @override
    @classmethod
    def get_from_xml(cls, xml: XML.Element) -> TwinCatPOU:
        (declaration,) = _find_tags(xml, "POU/Declaration", min=1, max=1)
        (implementation,) = _find_tags(xml, "POU/Implementation/ST", min=1, max=1)
        declaration_text = declaration.text or ""
        implementation_text = implementation.text or ""
        kind = cls._get_kind(declaration_text)
        pou = TwinCatPOU(kind, declaration_text, implementation_text, [], [])
        for property in _find_tags(xml, "POU/Property"):
            pou.properties.append(_get_property(property))
        for method in _find_tags(xml, "POU/Method"):
            pou.methods.append(_get_method(method))
        return pou
