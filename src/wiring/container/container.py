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
    ModuleWithoutProvider,
    CannotProvideUntilContainerIsSealed,
    CannotRegisterAfterContainerIsSealed,
)

T = TypeVar("T")


class Container:
    def __init__(self):
        self._modules: set[ModuleType] = set()
        self._module_providers: dict[ModuleType, ProviderType] = {}
        self._modules_without_providers: set[ModuleType] = set()
        self._is_sealed = False

    def register(self, module: ModuleType, provider: Optional[ProviderType] = None):
        if self._is_sealed:
            raise CannotRegisterAfterContainerIsSealed(module)
        if module in self._modules:
            raise ModuleAlreadyRegistered(module, self._modules)
        self._modules.add(module)
        self._modules_without_providers.add(module)
        if provider is not None:
            if provider.module is not module:
                raise ProviderModuleMismatch(provider, module)
            self._register_provider(provider, target=module)

    def seal(self) -> None:
        self._register_default_providers()
        self._is_sealed = True

    def register_provider(self, provider: ProviderType) -> None:
        if self._is_sealed:
            raise CannotRegisterAfterContainerIsSealed(provider)
        if provider.module not in self._modules:
            raise CannotRegisterProviderToUnknownModule(provider, self._modules)
        self._register_provider(provider, target=provider.module)

    def provide(self, resource: ResourceType[T]) -> T:
        if not self._is_sealed:
            raise CannotProvideUntilContainerIsSealed()
        target_module = resource.module
        if target_module not in self._module_providers:
            raise UnknownResource(resource, self._modules)
        provider = self._module_providers[target_module]
        provider_method = provider._get_provider_method(resource)
        return provider_method.method(None)  # fake provider instance.

    def _register_provider(self, provider: ProviderType, target: ModuleType):
        if target in self._module_providers:
            raise ModuleProviderAlreadyRegistered(target, provider)
        self._module_providers[target] = provider
        self._modules_without_providers.remove(target)

    def _register_default_providers(self):
        for module in self._modules_without_providers.copy():
            if module.default_provider is None:
                raise ModuleWithoutProvider(module)
            self._register_provider(module.default_provider, target=module)
