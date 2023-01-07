from __future__ import annotations
from typing import TypeVar, Type, Generic, TYPE_CHECKING

if TYPE_CHECKING:
    from .module import ModuleType

T = TypeVar("T")


class CannotRebindModule(Exception):
    def __init__(
        self, resource: ResourceType, rebind_name: str, rebind_module: ModuleType
    ):
        self.resource = resource
        self.rebind_name = rebind_name
        self.rebind_module = rebind_module


class ResourceIsNotBound(Exception):
    def __init__(self, resource: ResourceType):
        self.resource = resource


class ResourceType(Generic[T], type):
    type: Type[T]
    name: str
    module: ModuleType
    is_bound: bool

    def _bind(self, name: str, module: ModuleType):
        if self.is_bound:
            raise CannotRebindModule(self, name, module)
        self.name = name
        self.module = module
        self.is_bound = True

    def __getattr__(self, item):
        if not self.is_bound and item == "name" or item == "module":
            raise ResourceIsNotBound(self)

    @classmethod
    def make(cls, t: Type[T]) -> ResourceType[T]:
        return ResourceType("Resource", (), dict(type=t, is_bound=False))


def Resource(t: Type[T]) -> ResourceType[T]:
    return ResourceType.make(t)
