from __future__ import annotations
from typing import TypeVar, Generic, Type, TYPE_CHECKING, Any

from wiring.resource.errors import CannotRebindModule, ResourceIsNotBound

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType

T = TypeVar("T")


class ResourceType(Generic[T], type):
    type: Type[T]
    name: str
    module: ModuleType
    is_bound: bool

    def _bind(self, name: str, module: ModuleType) -> None:
        if self.is_bound:
            raise CannotRebindModule(self, name, module)
        self.name = name
        self.module = module
        self.is_bound = True

    def __getattr__(self, item: str) -> Any:
        if not self.is_bound and item == "name" or item == "module":
            raise ResourceIsNotBound(self)

    @classmethod
    def make(cls, t: Type[T]) -> ResourceType[T]:
        return ResourceType("Resource", (), dict(type=t, is_bound=False))
