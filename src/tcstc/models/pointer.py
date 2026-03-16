from dataclasses import dataclass
from typing import Generic, TypeVar

_T = TypeVar("_T")


@dataclass
class Pointer(Generic[_T]):
    value: _T
