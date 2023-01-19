from __future__ import annotations

import inspect
from typing import Any, Iterable, Optional, TYPE_CHECKING

from wiring.module.errors import (
    DefaultProviderIsNotAProvider,
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    InvalidResourceAnnotation,
    InvalidAttributeAnnotation,
    CannotUseExistingResource,
)
from wiring.resource import ResourceType

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType


class ModuleType(type):
    _resources_by_name: dict[str, ResourceType[Any]]
    _default_provider: Optional[ProviderType]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        self._resources_by_name = {}
        self._collect_resources(dct, inspect.get_annotations(self))
        self._default_provider = None

    def _collect_resources(
        self, dct: dict[str, Any], annotations: dict[str, Any]
    ) -> None:
        for name, candidate in dct.items():
            if name.startswith("_"):
                continue
            if isinstance(candidate, ResourceType):
                if candidate.is_bound:
                    raise CannotUseExistingResource(self, name, candidate)
                candidate.bind(name=name, module=self)
                self._resources_by_name[name] = candidate
            elif isinstance(candidate, type):
                resource: ResourceType[Any] = ResourceType.make_bound(
                    t=candidate, name=name, module=self  # pyright: ignore
                )
                self._resources_by_name[name] = resource
                setattr(self, name, resource)

        for name, annotation in annotations.items():
            if name.startswith("_") or name in self._resources_by_name:
                continue
            if isinstance(annotation, ResourceType):
                raise InvalidResourceAnnotation(self, name, annotation)
            if isinstance(annotation, type):
                raise InvalidAttributeAnnotation(self, name, annotation)

    def _list_resources(self) -> Iterable[ResourceType[Any]]:
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
