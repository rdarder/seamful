from typing import TypeVar, Optional, Type, cast

from wiring.container.raw_container import RawContainer
from wiring.resource import ResourceType
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType
from wiring.container.errors import (
    ProviderModuleMismatch,
    CannotProvideUntilContainerIsSealed,
    CannotRegisterAfterContainerIsSealed,
    CannotProvideRawType,
)

T = TypeVar("T")


class Container:
    def __init__(self) -> None:
        self._raw = RawContainer()
        self._is_sealed = False

    def register(
        self, module: ModuleType, provider: Optional[ProviderType] = None
    ) -> None:
        if self._is_sealed:
            raise CannotRegisterAfterContainerIsSealed(module)
        self._raw.register_public_module(module)
        if provider is not None:
            if provider.module is not module:
                raise ProviderModuleMismatch(provider, module)
            self._raw.register_provider(provider)

    def register_provider(self, provider: ProviderType) -> None:
        if self._is_sealed:
            raise CannotRegisterAfterContainerIsSealed(provider)
        self._raw.register_provider(provider)

    def seal(self) -> None:
        self._raw.solve_rest_of_graph()
        self._is_sealed = True

    def provide(self, resource: Type[T]) -> T:
        if not self._is_sealed:
            raise CannotProvideUntilContainerIsSealed()
        if not isinstance(resource, ResourceType):
            raise CannotProvideRawType(resource)
        as_resource = cast(ResourceType[T], resource)
        return self._raw.provide(as_resource)
