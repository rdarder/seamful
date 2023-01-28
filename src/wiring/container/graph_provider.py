from typing import Any, cast, TypeVar

from wiring.container.errors import (
    ModuleNotRegisteredForResource,
    ModuleNotKnownForResourceInternalError,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
)
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.resource import ModuleResource, ResourceTypes

T = TypeVar("T")


class ModuleGraphProvider:
    def __init__(
        self,
        registered_modules: set[ModuleType],
        providers_by_module: dict[ModuleType, ProviderType],
    ):
        self._registered_modules = registered_modules
        self._providers_by_module = providers_by_module
        self._instances_by_resource: dict[ModuleResource[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()

    def provide(self, resource: ResourceTypes[T]) -> T:
        if not isinstance(resource, ModuleResource):
            raise NotImplementedError()
        if resource.module not in self._registered_modules:
            raise ModuleNotRegisteredForResource(
                resource,
                self._registered_modules,
                set(self._providers_by_module.keys()),
            )

        return self._provide(resource)

    def _provide(self, resource: ResourceTypes[T]) -> T:
        if not isinstance(resource, ModuleResource):
            raise NotImplementedError()
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        target_module = resource.module
        if target_module not in self._providers_by_module:
            raise ModuleNotKnownForResourceInternalError(
                resource, set(self._providers_by_module.keys())
            )
        provider = self._providers_by_module[target_module]
        provider_method: ProviderMethod[T] = provider._get_provider_method(resource)
        method_parameters = {
            name: self._provide(resource)
            for name, resource in provider_method.dependencies.items()
        }
        try:
            instance = provider_method.method(
                self._fake_provider_instance, **method_parameters
            )
        except InvalidProviderInstanceAccess:
            raise ProviderMethodsCantAccessProviderInstance(
                provider, resource, provider_method
            )
        self._instances_by_resource[resource] = instance
        return instance


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
