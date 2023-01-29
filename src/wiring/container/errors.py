from __future__ import annotations
from dataclasses import dataclass
from typing import Union, Any, Type, cast, TYPE_CHECKING

from wiring.module.module_type import ModuleType
from wiring.resource import ModuleResource, ResourceTypes, PrivateResource
from wiring.provider.provider_type import ProviderType, ProviderMethod

if TYPE_CHECKING:
    from wiring.container import Container
    from wiring.container.registry import Registry


class ModuleNotRegisteredForResource(Exception):
    def __init__(
        self,
        resource: ResourceTypes[Any],
        registered_modules: set[ModuleType],
        known_modules: set[ModuleType],
    ):
        self.resource = resource
        self.registered_modules = registered_modules
        self.known_modules = known_modules


class ModuleAlreadyRegistered(Exception):
    def __init__(self, module: ModuleType, registered_modules: set[ModuleType]):
        self.module = module
        self.registered_modules = registered_modules


class ProviderModuleMismatch(Exception):
    def __init__(self, provider: ProviderType, module: ModuleType):
        self.provider = provider
        self.module = module


class CannotRegisterProviderToNotRegisteredModule(Exception):
    def __init__(self, provider: ProviderType, registered_modules: set[ModuleType]):
        self.provider = provider
        self.registered_modules = registered_modules


class CannotOverrideRegisteredProvider(Exception):
    def __init__(
        self, module: ModuleType, *, registered: ProviderType, registering: ProviderType
    ):
        self.module = module
        self.registered = registered
        self.registering = registering


class ModuleWithoutRegisteredOrDefaultProvider(Exception):
    def __init__(self, module: ModuleType):
        self.module = module


class CannotProvideUntilRegistrationsAreClosed(Exception):
    pass


class RegistrationsAreClosed(Exception):
    def __init__(self, registering: Union[ModuleType, ProviderType]):
        self.registering = registering


class CannotProvideRawType(Exception):
    def __init__(self, t: type):
        self.type = t


@dataclass(frozen=True)
class ResolutionStep:
    target: ResourceTypes[Any]
    provider_method: ProviderMethod[Any]
    parameter_name: str
    depends_on: ResourceTypes[Any]

    @classmethod
    def from_types(
        cls,
        target: Type[Any],
        provider_method: ProviderMethod[Any],
        parameter_name: str,
        depends_on: Type[Any],
    ) -> ResolutionStep:
        return ResolutionStep(
            target=cast(ResourceTypes[Any], target),
            provider_method=provider_method,
            parameter_name=parameter_name,
            depends_on=cast(ModuleResource[Any], depends_on),
        )


class CircularDependency(Exception):
    def __init__(self, loop: list[ResolutionStep]):
        self.loop = loop


class InvalidProviderInstanceAccess(Exception):
    pass


class ProviderMethodsCantAccessProviderInstance(Exception):
    def __init__(
        self,
        resource: ResourceTypes[Any],
        provider_method: ProviderMethod[Any],
    ):
        self.resource = resource
        self.provider_method = provider_method


class UnexpectedCoreContainerNotReady(Exception):
    def __init__(self, container: Container, core: Registry):
        self.container = container
        self.core = core


class RegistrationMustBeClosedBeforeReopeningThem(Exception):
    def __init__(self, container: Container) -> None:
        self.container = container


class ContainerAlreadyReadyForProvisioning(Exception):
    pass


class CannotReopenRegistrationsAfterHavingProvidedResources(Exception):
    pass


class RegisteredProvidersNotUsed(Exception):
    def __init__(self, providers: set[ProviderType]):
        self.providers = providers


class ProviderNotProvidingForModule(Exception):
    def __init__(self, resource: PrivateResource[Any], provider_in_use: ProviderType):
        self.resource = resource
        self.provider_in_use = provider_in_use
