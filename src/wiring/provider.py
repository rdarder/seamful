from __future__ import annotations
from dataclasses import dataclass
from typing import Any, TYPE_CHECKING, get_args, Generic, TypeVar

from .resource import ResourceType

if TYPE_CHECKING:
    from .module import ModuleType


class ProviderType(type):
    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        if self._is_base_provider_class(bases):
            return
        self.module = self._determine_module_from_generic_argument(dct)
        self._provider_methods_by_resource: dict[ResourceType, ProviderMethod] = {}
        self._collect_provider_methods()

    def _is_base_provider_class(self, bases) -> bool:
        return len(bases) == 1 and bases[0] is Generic

    def _collect_provider_methods(self):
        for resource in self.module._list_resources():
            method = getattr(self, f"provide_{resource.name}", None)
            if method is None:
                raise MissingProviderMethod(resource, self)
            if not callable(method):
                raise ProviderMethodNotCallable(resource, self)
            provider_method = ProviderMethod(method, self, resource)
            self._provider_methods_by_resource[resource] = provider_method

    def _determine_module_from_generic_argument(self, dct) -> ModuleType:
        from .module import ModuleType, Module  # circular import

        bases = dct.get("__orig_bases__")
        if bases is None or len(bases) == 0:
            raise MissingProviderModuleAnnotation(self)
        generic_provider = bases[0]
        module = get_args(generic_provider)[0]
        if not isinstance(module, ModuleType):
            raise InvalidProviderModuleAnnotation(self, module)
        if module is Module:
            raise CannotProvideBaseModule(self)
        return module

    def _get_provider_method(self, resource: ResourceType) -> ProviderMethod:
        if resource.module is not self.module:
            raise UnrelatedResource(self, resource)
        provider_method = self._provider_methods_by_resource.get(resource)
        if provider_method is None:
            # This should always be present. this would be an invalid state.
            raise ProviderMethodNotFound(self, resource)
        return provider_method


@dataclass
class ProviderMethod:
    method: callable
    provider: ProviderType
    resource: ResourceType


class MissingProviderMethod(Exception):
    def __init__(self, resource: ResourceType, provider: ProviderType):
        self.resource = resource
        self.provider = provider


class ProviderMethodNotCallable(Exception):
    def __init__(self, resource: ResourceType, provider: ProviderType):
        self.resource = resource
        self.provider = provider


class MissingProviderModuleAnnotation(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class InvalidProviderModuleAnnotation(Exception):
    def __init__(self, provider: ProviderType, invalid_module: Any):
        self.provider = provider
        self.invalid_module = invalid_module


class CannotProvideBaseModule(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class ProviderMethodNotFound(Exception):
    # This means there's a problem with the implementation than a user error.
    def __init__(self, provider: ProviderType, resource: ResourceType):
        self.provider = provider
        self.resource = resource


class UnrelatedResource(Exception):
    def __init__(self, provider: ProviderType, resource: ResourceType):
        self.provider = provider
        self.resource = resource


M = TypeVar("M")


class Provider(Generic[M], metaclass=ProviderType):
    pass
