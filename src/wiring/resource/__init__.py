from __future__ import annotations

from typing import TypeVar, Generic, Type, TYPE_CHECKING, Union, Any

from wiring.resources.errors import CannotMakePrivateOverridingResource

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType
    from wiring.provider.provider_type import ProviderType

T = TypeVar("T")


class ModuleResource(Generic[T]):
    type: Type[T]
    name: str
    module: ModuleType
    is_bound: bool

    def __init__(self, type: Type[T]):
        self.type = type
        self.is_bound = False

    def bind(self, name: str, module: ModuleType) -> None:
        self.name = name
        self.module = module
        self.is_bound = True

    @staticmethod
    def make_unbound(t: Type[T]) -> ModuleResource[T]:
        return ModuleResource(t)

    @staticmethod
    def make_bound(t: Type[T], name: str, module: ModuleType) -> ModuleResource[T]:
        resource = ModuleResource(t)
        resource.bind(name, module)
        return resource

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound module resource.")
        return hash((self.__class__, self.type, self.name, self.module))

    def __repr__(self) -> str:
        if self.is_bound:
            return f"ModuleResource('{self.name}', {self.type.__name__}, {self.module.__name__})"
        else:
            return f"Unbound ModuleResource({self.type})"


class PrivateResource(Generic[T]):
    type: Type[T]
    name: str
    provider: ProviderType
    is_bound: bool
    module: ModuleType

    def __init__(self, type: Type[T]):
        self.type = type
        self.is_bound = False

    def bind(self, name: str, provider: ProviderType) -> None:
        self.name = name
        self.provider = provider
        self.module = provider.module
        self.is_bound = True

    def bound_to_sub_provider(self, provider: ProviderType) -> PrivateResource[T]:
        return PrivateResource.make_bound(self.type, self.name, provider)

    @staticmethod
    def make_unbound(t: Type[T]) -> PrivateResource[T]:
        return PrivateResource(t)

    @staticmethod
    def make_bound(t: Type[T], name: str, provider: ProviderType) -> PrivateResource[T]:
        resource = PrivateResource(t)
        resource.bind(name, provider)
        return resource

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound provider resource.")
        return hash((self.__class__, self.type, self.name, self.provider))

    def __repr__(self) -> str:
        if self.is_bound:
            return (
                f"PrivateResource('{self.name}', {self.type.__name__}, "
                f"{self.provider.__name__})"
            )
        else:
            return f"Unbound PrivateResource({self.type})"


class OverridingResource(Generic[T]):
    type: Type[T]
    name: str
    provider: ProviderType
    module: ModuleType
    overrides: ModuleResource[T]
    is_bound: bool

    def __init__(self, t: Type[T]):
        self.type = t
        self.is_bound = False

    def bind(
        self, name: str, provider: ProviderType, overrides: ModuleResource[T]
    ) -> None:
        self.name = name
        self.provider = provider
        self.module = provider.module
        self.overrides = overrides
        self.is_bound = True

    def bound_to_sub_provider(self, provider: ProviderType) -> OverridingResource[T]:
        return OverridingResource.make_bound(
            self.type, self.name, provider, self.overrides
        )

    @staticmethod
    def make_unbound(t: Type[T]) -> OverridingResource[T]:
        return OverridingResource(t)

    @staticmethod
    def make_bound(
        t: Type[T], name: str, provider: ProviderType, overrides: ModuleResource[Any]
    ) -> OverridingResource[T]:
        resource = OverridingResource(t)
        resource.bind(name, provider, overrides)
        return resource

    def __hash__(self) -> int:
        if not self.is_bound:
            raise Exception("Unhashable unbound provider resource.")
        return hash(
            (self.__class__, self.type, self.name, self.provider, self.overrides)
        )

    def __repr__(self) -> str:
        if self.is_bound:
            return (
                f"OverridingResource('{self.name}', {self.type.__name__}, "
                f"{self.provider.__name__}, {self.module.__name__})"
            )
        else:
            return f"Unbound OverridingResource({self.type})"


ResourceTypes = Union[ModuleResource[T], PrivateResource[T], OverridingResource[T]]
RESOURCE_TYPES = (ModuleResource, PrivateResource, OverridingResource)
ProviderResourceTypes = Union[PrivateResource[T], OverridingResource[T]]


def Resource(t: Type[T], private: bool = False, override: bool = False) -> Type[T]:
    if private and override:
        raise CannotMakePrivateOverridingResource()
    elif private:
        return PrivateResource.make_unbound(t)  # type: ignore
    elif override:
        return OverridingResource.make_unbound(t)  # type: ignore
    else:
        return ModuleResource.make_unbound(t)  # type: ignore
