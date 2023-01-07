from typing import Any, Iterable

from .resource import Resource, ResourceType


class ModuleType(type):
    _resources_by_name: dict[str, Resource]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        self._resources_by_name = {}
        self._collect_resources(dct)

    def _collect_resources(self, dct: dict[str, Any]):
        for name, candidate in dct.items():
            if isinstance(candidate, ResourceType):
                candidate._bind(name, self)
                self._resources_by_name[name] = candidate

    def _list_resources(self) -> Iterable[Resource]:
        return self._resources_by_name.values()


class Module(metaclass=ModuleType):
    pass
