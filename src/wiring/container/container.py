from typing import TypeVar, Optional

from wiring.resource import ResourceType
from wiring.module import ModuleType
from wiring.provider.provider_type import ProviderType

from .errors import (
    UnknownResource,
    ModuleAlreadyRegistered,
    ProviderModuleMismatch,
    CannotRegisterProviderToUnknownModule,
    ModuleProviderAlreadyRegistered,
)

T = TypeVar("T")


class Container:
    def __init__(self):
        self._modules: set[ModuleType] = set()
        self._module_providers: dict[ModuleType, ProviderType] = {}

    def register(self, module: ModuleType, provider: Optional[ProviderType] = None):
        if module in self._modules:
            raise ModuleAlreadyRegistered(module, self._modules)
        self._modules.add(module)
        if provider is not None:
            if provider.module is not module:
                raise ProviderModuleMismatch(provider, module)
            self._register_provider(provider, target=module)

    def register_provider(self, provider: ProviderType) -> None:
        if provider.module not in self._modules:
            raise CannotRegisterProviderToUnknownModule(provider, self._modules)
        self._register_provider(provider, target=provider.module)

    def _register_provider(self, provider: ProviderType, target: ModuleType):
        if target in self._module_providers:
            raise ModuleProviderAlreadyRegistered(target, provider)
        self._module_providers[target] = provider

    def provide(self, resource: ResourceType[T]) -> T:
        target_module = resource.module
        if target_module not in self._module_providers:
            raise UnknownResource(resource, self._modules)
        provider = self._module_providers[target_module]
        provider_method = provider._get_provider_method(resource)
        return provider_method.method(None)  # fake provider instance.
