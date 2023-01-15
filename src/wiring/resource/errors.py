from __future__ import annotations
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType
    from wiring.resource.resource_type import ResourceType


class CannotRebindModule(Exception):
    def __init__(
        self, resource: ResourceType[Any], rebind_name: str, rebind_module: ModuleType
    ):
        self.resource = resource
        self.rebind_name = rebind_name
        self.rebind_module = rebind_module


class ResourceIsNotBound(Exception):
    def __init__(self, resource: ResourceType[Any]):
        self.resource = resource
