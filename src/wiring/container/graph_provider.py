from typing import Any, cast, TypeVar

from wiring.container.errors import (
    ModuleNotRegisteredForResource,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
    ProviderNotProvidingForModule,
)
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType
from wiring.resource import (
    ModuleResource,
    ResourceTypes,
    PrivateResource,
    OverridingResource,
)

T = TypeVar("T")


class ProviderResourcesNotAllowed(Exception):
    def __init__(self, resource: PrivateResource[Any] | OverridingResource[Any]):
        self.resource = resource


class ModuleGraphProvider:
    def __init__(
        self,
        registered_modules: set[ModuleType],
        providers_by_module: dict[ModuleType, ProviderType],
        allow_provider_resources: bool,
    ):
        self._registered_modules = registered_modules
        self._providers = providers_by_module
        self._instances_by_resource: dict[ResourceTypes[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()
        self._allow_provider_resources = allow_provider_resources

    def provide(self, resource: ResourceTypes[T]) -> T:
        self._ensure_known_module(resource)
        if isinstance(resource, ModuleResource):
            return self._provide(resource)
        else:
            if not self._allow_provider_resources:
                raise ProviderResourcesNotAllowed(resource)
            if resource.provider is not self._providers[resource.provider.module]:
                raise ProviderNotProvidingForModule(
                    resource, self._providers[resource.provider.module]
                )
            return self._provide(resource)

    def _ensure_known_module(self, resource: ResourceTypes[Any]) -> None:
        if resource.module not in self._registered_modules:
            raise ModuleNotRegisteredForResource(
                resource,
                self._registered_modules,
                set(self._providers.keys()),
            )

    def _provide(self, resource: ResourceTypes[T]) -> T:
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        if type(resource) is OverridingResource:
            return self._provide(resource.overrides)

        provider_method = self._providers[resource.module]._get_provider_method(
            resource
        )
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


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
