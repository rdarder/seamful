from __future__ import annotations
from typing import Any, Iterable, Optional, TYPE_CHECKING

from wiring.module.errors import (
    DefaultProviderIsNotAProvider,
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
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
        self._collect_resources(dct)
        self._default_provider = None

    def _collect_resources(self, dct: dict[str, Any]) -> None:
        for name, candidate in dct.items():
            if name.startswith("_"):
                continue
            if isinstance(candidate, ResourceType) and not candidate.is_bound:
                candidate.bind(name=name, module=self)
                self._resources_by_name[name] = candidate
            elif isinstance(candidate, type):
                resource: ResourceType[Any] = ResourceType.make_bound(
                    t=candidate, name=name, module=self  # pyright: ignore
                )
                self._resources_by_name[name] = resource
                setattr(self, name, resource)

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
