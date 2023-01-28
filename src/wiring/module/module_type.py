from __future__ import annotations

import inspect
from typing import Any, Iterable, Optional, TYPE_CHECKING

from wiring.module.errors import (
    DefaultProviderIsNotAProvider,
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    InvalidModuleResourceAnnotationInModule,
    InvalidAttributeAnnotationInModule,
    CannotUseExistingModuleResource,
    ModulesCannotBeInstantiated,
    InvalidProviderResourceAnnotationInModule,
)
from wiring.resource import ModuleResource, ProviderResource

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType


class CannotDefinePrivateResourceInModule(Exception):
    def __init__(self, module: ModuleType, name: str, t: type):
        self.module = module
        self.name = name
        self.type = t


class ModuleType(type):
    _resources_by_name: dict[str, ModuleResource[Any]]
    _default_provider: Optional[ProviderType]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        self._resources_by_name = {}
        self._collect_resources(dct, inspect.get_annotations(self))
        self._default_provider = None

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ModulesCannotBeInstantiated(self)

    def _collect_resources(
        self, dct: dict[str, Any], annotations: dict[str, Any]
    ) -> None:
        for name, candidate in dct.items():
            if name.startswith("_"):
                continue
            if isinstance(candidate, ModuleResource):
                if candidate.is_bound:
                    raise CannotUseExistingModuleResource(self, name, candidate)
                candidate.bind(name=name, module=self)
                self._resources_by_name[name] = candidate
            elif isinstance(candidate, ProviderResource):
                raise CannotDefinePrivateResourceInModule(self, name, candidate.type)
            elif isinstance(candidate, type):
                resource: ModuleResource[Any] = ModuleResource.make_bound(
                    t=candidate, name=name, module=self  # pyright: ignore
                )
                self._resources_by_name[name] = resource
                setattr(self, name, resource)

        for name, annotation in annotations.items():
            if name.startswith("_") or name in self._resources_by_name:
                continue
            if isinstance(annotation, ModuleResource):
                raise InvalidModuleResourceAnnotationInModule(self, name, annotation)
            if isinstance(annotation, ProviderResource):
                raise InvalidProviderResourceAnnotationInModule(self, name, annotation)
            if isinstance(annotation, type):
                raise InvalidAttributeAnnotationInModule(self, name, annotation)

    def _list_resources(self) -> Iterable[ModuleResource[Any]]:
        return self._resources_by_name.values()

    @property
    def default_provider(self) -> Optional[ProviderType]:
        return self._default_provider

    @default_provider.setter
    def default_provider(self, provider: ProviderType) -> None:
        from wiring.provider.provider_type import ProviderType
        from wiring.provider.provider import Provider

        if not isinstance(provider, ProviderType):
            raise DefaultProviderIsNotAProvider(self, provider)
        if provider is Provider:
            raise CannotUseBaseProviderAsDefaultProvider(self)
        if provider.module is not self:
            raise DefaultProviderProvidesToAnotherModule(self, provider)
        self._default_provider = provider
