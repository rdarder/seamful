from __future__ import annotations
from typing import TypeVar, Optional, Type, cast

from wiring.container.registry import Registry
from wiring.container.graph_provider import ModuleGraphProvider
from wiring.resource import BoundResource
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType
from wiring.container.errors import (
    ProviderModuleMismatch,
    RegistrationsAreClosed,
    CannotProvideRawType,
    CannotProvideUntilRegistrationsAreClosed,
    CannotTamperUntilContainerIsReady,
    ContainerAlreadyReady,
    CannotTamperAfterHavingProvidedResources,
    CannotTamperWithContainerTwice,
    ContainerWasNotTamperedWith,
)

T = TypeVar("T")


class Container:
    def __init__(self) -> None:
        self._is_registering = True
        self._is_providing = False

        self._checkpoint: Optional[tuple[Registry, ModuleGraphProvider]] = None
        self._registry: Registry = Registry.empty()
        self._provider: Optional[ModuleGraphProvider] = None

        self._allow_overrides = False
        self._allow_implicit_modules = False

    def register(self, module: ModuleType, provider: Optional[ProviderType] = None) -> None:
        if not self._is_registering:
            raise RegistrationsAreClosed(module)
        self._registry.register_module(module)
        if provider is not None:
            if provider.module is not module:
                raise ProviderModuleMismatch(provider, module)
            self._registry.register_provider(
                provider,
                allow_override=self._allow_overrides,
                allow_implicit_module=False,
            )

    def register_provider(self, provider: ProviderType) -> None:
        if not self._is_registering:
            raise RegistrationsAreClosed(provider)
        self._registry.register_provider(
            provider,
            allow_override=self._allow_overrides,
            allow_implicit_module=self._allow_implicit_modules,
        )

    def ready(self, allow_provider_resources: bool = False) -> None:
        if not self._is_registering:
            raise ContainerAlreadyReady(self)
        self._provider = self._registry.solve_graph(allow_provider_resources)
        self._is_registering = False

    def provide(self, resource: Type[T]) -> T:
        if self._is_registering:
            raise CannotProvideUntilRegistrationsAreClosed()
        if not self._is_providing:
            self._is_providing = True
            self._registry = None  # type: ignore
        if isinstance(resource, BoundResource):
            as_resource = cast(BoundResource[T], resource)
            return self._provider.provide(as_resource)  # pyright: ignore
        elif isinstance(resource, type):
            raise CannotProvideRawType(resource)
        else:
            raise NotImplementedError()

    def tamper(
        self,
        *,
        allow_overrides: bool = False,
        allow_implicit_modules: bool = False,
    ) -> None:
        if self._is_providing:
            raise CannotTamperAfterHavingProvidedResources(self)
        if self._is_registering:
            raise CannotTamperUntilContainerIsReady(self)
        if self._checkpoint is not None:
            raise CannotTamperWithContainerTwice(self)
        self._checkpoint = (self._registry, cast(ModuleGraphProvider, self._provider))
        self._registry = self._registry.copy()
        self._provider = None
        self._is_registering = True
        self._allow_overrides = allow_overrides
        self._allow_implicit_modules = allow_implicit_modules

    def restore(self) -> None:
        if self._checkpoint is None:
            raise ContainerWasNotTamperedWith(self)
        self._registry, self._provider = self._checkpoint
        self._checkpoint = None
        self._is_registering = False
        self._is_providing = False

    @classmethod
    def empty(cls) -> Container:
        return Container()
