from __future__ import annotations

from typing import TypeVar, Generic, Type, TYPE_CHECKING, Union

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType
    from wiring.provider.provider_type import ProviderType

T = TypeVar("T")


class ModuleResource(Generic[T], type):
    type: Type[T]
    name: str
    module: ModuleType
    is_bound: bool

    def bind(self, name: str, module: ModuleType) -> None:
        self.name = name
        self.module = module
        self.is_bound = True

    @staticmethod
    def make_unbound(t: Type[T]) -> ModuleResource[T]:
        return ModuleResource("ModuleResource", (), dict(type=t, is_bound=False))

    @staticmethod
    def make_bound(t: Type[T], name: str, module: ModuleType) -> ModuleResource[T]:
        return ModuleResource(
            "ModuleResource", (), dict(type=t, name=name, module=module, is_bound=True)
        )

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound module resource.")
        return hash((self.__class__, self.type, self.name, self.module))

    def __repr__(self) -> str:
        if self.is_bound:
            return f"ModuleResource('{self.name}', {self.type.__name__}, {self.module.__name__})"
        else:
            return f"Unbound ModuleResource({self.type})"


class ProviderResource(Generic[T], type):
    type: Type[T]
    name: str
    provider: ProviderType
    is_bound: bool
    module: ModuleType

    def bind(self, name: str, provider: ProviderType) -> None:
        self.name = name
        self.provider = provider
        self.module = provider.module
        self.is_bound = True

    @staticmethod
    def make_unbound(t: Type[T]) -> ProviderResource[T]:
        return ProviderResource("ProviderResource", (), dict(type=t, is_bound=False))

    @staticmethod
    def make_bound(
        t: Type[T], name: str, provider: ProviderType
    ) -> ProviderResource[T]:
        return ProviderResource(
            "ProviderResource",
            (),
            dict(
                type=t,
                name=name,
                provider=provider,
                module=provider.module,
                is_bound=True,
            ),
        )

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound provider resource.")
        return hash((self.__class__, self.type, self.name, self.provider))

    def __repr__(self) -> str:
        if self.is_bound:
            return (
                f"ProviderResource('{self.name}', {self.type.__name__}, "
                f"{self.provider.__name__})"
            )
        else:
            return f"Unbound ProviderResource({self.type})"


ResourceTypes = Union[ModuleResource[T], ProviderResource[T]]
RESOURCE_TYPES = (ModuleResource, ProviderResource)


def Resource(t: Type[T], private: bool = False) -> Type[T]:
    if private:
        return ProviderResource.make_unbound(t)  # type: ignore
    else:
        return ModuleResource.make_unbound(t)  # type: ignore
