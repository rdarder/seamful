from __future__ import annotations

from typing import TypeVar, Generic, Type, TYPE_CHECKING

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType

T = TypeVar("T")


class ResourceType(Generic[T], type):
    type: Type[T]
    name: str
    module: ModuleType
    is_bound: bool

    def bind(self, name: str, module: ModuleType) -> None:
        self.name = name
        self.module = module
        self.is_bound = True

    @staticmethod
    def make_unbound(t: Type[T]) -> ResourceType[T]:
        return ResourceType("ResourceType", (), dict(type=t, is_bound=False))

    @staticmethod
    def make_bound(t: Type[T], name: str, module: ModuleType) -> ResourceType[T]:
        return ResourceType(
            "ResourceType", (), dict(type=t, name=name, module=module, is_bound=True)
        )

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound resource.")
        return hash((self.__class__, self.type, self.name, self.module))


R = TypeVar("R")


def Resource(t: Type[T]) -> Type[T]:
    return ResourceType.make_unbound(t)  # type: ignore
