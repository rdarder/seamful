from __future__ import annotations
from dataclasses import dataclass
from typing import TypeVar, Generic, Type

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType

T = TypeVar("T")


@dataclass(frozen=True)
class ResourceType(Generic[T]):
    type: Type[T]
    name: str
    module: ModuleType
