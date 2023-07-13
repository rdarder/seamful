from typing import Any, cast, TypeVar, Set, Dict

from seamful.application.errors import (
    ModuleNotRegisteredForResource,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
    ProviderResourceOfUnregisteredProvider,
)
from seamful.module.module_type import ModuleType
from seamful.provider.provider_type import ProviderType
from seamful.resource import (
    ModuleResource,
    OverridingResource,
    ProviderResource,
    BoundResource,
)

T = TypeVar("T")


class ProviderResourcesNotAllowed(Exception):
    def __init__(self, resource: ProviderResource[Any]):
        self.resource = resource


class ModuleGraphProvider:
    def __init__(
        self,
        registered_modules: Set[ModuleType],
        providers_by_module: Dict[ModuleType, ProviderType],
        allow_provider_resources: bool,
    ):
        self._registered_modules = registered_modules
        self._providers = providers_by_module
        self._instances_by_resource: Dict[BoundResource[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()
        self._allow_provider_resources = allow_provider_resources

    def provide(self, resource: BoundResource[T]) -> T:
        self._ensure_known_module(resource)
        if isinstance(resource, ModuleResource):
            return self._provide(cast(ModuleResource[T], resource))
        elif isinstance(resource, ProviderResource):
            if not self._allow_provider_resources:
                raise ProviderResourcesNotAllowed(resource)
            if resource.provider is not self._providers[resource.provider.module]:
                raise ProviderResourceOfUnregisteredProvider(
                    resource, self._providers[resource.provider.module]
                )
            return self._provide(cast(ProviderResource[T], resource))
        else:
            raise TypeError()

    def _ensure_known_module(self, resource: BoundResource[Any]) -> None:
        if resource.module not in self._registered_modules:
            raise ModuleNotRegisteredForResource(
                resource,
                self._registered_modules,
                set(self._providers.keys()),
            )

    def _provide(self, resource: BoundResource[T]) -> T:
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        if isinstance(resource, OverridingResource):
            return self._provide(cast(OverridingResource[T], resource.overrides))

        provider_method = self._providers[resource.module][resource]
        method_parameters = {
            name: self._provide(resource) for name, resource in provider_method.dependencies
        }
        try:
            instance = provider_method.method(self._fake_provider_instance, **method_parameters)
        except InvalidProviderInstanceAccess:
            raise ProviderMethodsCantAccessProviderInstance(resource, provider_method)
        self._instances_by_resource[resource] = instance
        return instance


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
