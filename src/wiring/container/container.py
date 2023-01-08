from typing import TypeVar

from wiring.resource import ResourceType
from wiring.module import ModuleType
from wiring.provider import ProviderType

from .errors import UnknownResource, ModuleAlreadyRegistered, ProviderModuleMismatch

T = TypeVar("T")


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
