from typing import TypeVar

from .resource import Resource, ResourceType
from .module import ModuleType
from .provider import ProviderType

T = TypeVar("T")


class UnknownResource(Exception):
    def __init__(self, resource: Resource, known_modules: set[ModuleType]):
        self.resource = resource
        self.known_modules = known_modules


class ModuleAlreadyRegistered(Exception):
    def __init__(self, module: ModuleType, known_modules: set[ModuleType]):
        self.module = module
        self.known_modules = known_modules


class ProviderModuleMismatch(Exception):
    def __init__(self, provider: ProviderType, module: ModuleType):
        self.provider = provider
        self.module = module


class Container:
    def __init__(self):
        self._modules: set[ModuleType] = set()
        self._module_providers: dict[ModuleType, ProviderType] = {}

    def register(self, module: ModuleType, provider: ProviderType):
        if module in self._modules:
            raise ModuleAlreadyRegistered(module, self._modules)
        if provider.module is not module:
            raise ProviderModuleMismatch(provider, module)
        self._modules.add(module)
        self._module_providers[module] = provider

    def provide(self, resource: ResourceType[T]) -> T:
        target_module = resource.module
        if target_module not in self._module_providers:
            raise UnknownResource(resource, self._modules)
        provider = self._module_providers[target_module]
        provider_method = provider._get_provider_method(resource)
        return provider_method.method(None)  # fake provider instance.
