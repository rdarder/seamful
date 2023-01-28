from typing import Any, cast, TypeVar

from wiring.container.errors import (
    ModuleNotRegisteredForResource,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
    ProviderNotProvidingForModule,
)
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.resource import ModuleResource, ResourceTypes, ProviderResource

T = TypeVar("T")


class ModuleGraphProvider:
    def __init__(
        self,
        registered_modules: set[ModuleType],
        providers_by_module: dict[ModuleType, ProviderType],
    ):
        self._registered_modules = registered_modules
        self._providers_by_module = providers_by_module
        self._instances_by_resource: dict[ResourceTypes[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()

    def provide(self, resource: ResourceTypes[T]) -> T:
        if type(resource) is ModuleResource:
            if resource.module not in self._registered_modules:
                raise ModuleNotRegisteredForResource(
                    resource,
                    self._registered_modules,
                    set(self._providers_by_module.keys()),
                )
        elif type(resource) is ProviderResource:
            if resource.provider.module not in self._registered_modules:
                raise ModuleNotRegisteredForResource(
                    resource,
                    self._registered_modules,
                    set(self._providers_by_module.keys()),
                )
            if (
                resource.provider
                is not self._providers_by_module[resource.provider.module]
            ):
                raise ProviderNotProvidingForModule(
                    resource, self._providers_by_module[resource.provider.module]
                )

        return self._provide(resource)

    def _provide(self, resource: ResourceTypes[T]) -> T:
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        provider_method = self._get_provider_method_for_resource(resource)
        method_parameters = {
            name: self._provide(resource)
            for name, resource in provider_method.dependencies.items()
        }
        try:
            instance = provider_method.method(
                self._fake_provider_instance, **method_parameters
            )
        except InvalidProviderInstanceAccess:
            raise ProviderMethodsCantAccessProviderInstance(resource, provider_method)
        self._instances_by_resource[resource] = instance
        return instance

    def _get_provider_method_for_resource(
        self, resource: ResourceTypes[T]
    ) -> ProviderMethod[T]:
        if type(resource) is ModuleResource:
            module = resource.module
        elif type(resource) is ProviderResource:
            module = resource.provider.module
        else:
            raise TypeError()

        provider = self._providers_by_module[module]
        return provider._get_provider_method(resource)


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
