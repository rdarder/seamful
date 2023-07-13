from __future__ import annotations

from typing import Any, Optional, TYPE_CHECKING, Iterator

from seamful.module.errors import (
    DefaultProviderIsNotAProvider,
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    CannotUseExistingModuleResource,
    ModulesCannotBeInstantiated,
    InvalidPrivateResourceInModule,
    InvalidOverridingResourceInModule,
    ModulesMustInheritDirectlyFromModuleClass,
    InvalidModuleAttributeType,
    InvalidPrivateModuleAttribute,
    InvalidModuleAttributeName,
)
from seamful.resource import (
    ModuleResource,
    UnboundResource,
    ProviderResource,
    ResourceKind,
)

if TYPE_CHECKING:
    from seamful.provider.provider_type import ProviderType


class ModuleType(type):
    _resources_by_name: dict[str, ModuleResource[Any]]
    _resources: set[ModuleResource[Any]]
    _default_provider: Optional[ProviderType]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        self._resources = set()
        self._resources_by_name = {}
        self._default_provider = None
        type.__init__(self, name, bases, dct)
        if len(bases) == 0:
            return
        if bases[0] != Module:
            raise ModulesMustInheritDirectlyFromModuleClass(name, bases)
        self._collect_resources(dct)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ModulesCannotBeInstantiated(self)

    def __contains__(self, item: str | ModuleResource[Any]) -> bool:
        if type(item) is ModuleResource:
            return item in self._resources
        elif type(item) is str:
            return item in self._resources_by_name
        else:
            raise TypeError()

    def __iter__(self) -> Iterator[ModuleResource[Any]]:
        return iter(self._resources)

    def __getitem__(self, name: str) -> ModuleResource[Any]:
        return self._resources_by_name[name]

    @property
    def default_provider(self) -> Optional[ProviderType]:
        return self._default_provider

    @default_provider.setter
    def default_provider(self, provider: ProviderType) -> None:
        from seamful.provider.provider_type import Provider, ProviderType

        if not isinstance(provider, ProviderType):
            raise DefaultProviderIsNotAProvider(self, provider)
        if provider is Provider:
            raise CannotUseBaseProviderAsDefaultProvider(self)
        if provider.module is not self:
            raise DefaultProviderProvidesToAnotherModule(self, provider)
        self._default_provider = provider

    def _collect_resources(self, dct: dict[str, Any]) -> None:
        for name, candidate in dct.items():
            if name.startswith("__"):
                continue
            resource = self._turn_attribute_into_resource(name, candidate)
            self._add_resource(resource)

    def _turn_attribute_into_resource(self, name: str, candidate: Any) -> ModuleResource[Any]:
        if name.startswith("_"):
            raise InvalidPrivateModuleAttribute(self, name, candidate)
        elif name == "default_provider":
            raise InvalidModuleAttributeName(self, name, candidate)
        if isinstance(candidate, UnboundResource):
            if candidate.kind == ResourceKind.OVERRIDE:
                raise InvalidOverridingResourceInModule(self, name, candidate.type)
            elif candidate.kind == ResourceKind.PRIVATE:
                raise InvalidPrivateResourceInModule(self, name, candidate.type)
            return ModuleResource(candidate.type, name, self)
        elif isinstance(candidate, ModuleResource):
            raise CannotUseExistingModuleResource(self, name, candidate)
        elif isinstance(candidate, ProviderResource):
            raise InvalidPrivateResourceInModule(self, name, candidate.type)
        elif isinstance(candidate, type):
            return ModuleResource[Any](candidate, name, self)
        else:
            raise InvalidModuleAttributeType(self, name, candidate)

    def _add_resource(self, resource: ModuleResource[Any]) -> None:
        self._resources.add(resource)
        self._resources_by_name[resource.name] = resource
        setattr(self, resource.name, resource)


class Module(metaclass=ModuleType):
    pass
