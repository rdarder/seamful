from __future__ import annotations
from dataclasses import dataclass
from typing import Union, Any, Type, cast

from wiring.module.module_type import ModuleType
from wiring.resource import ResourceType
from wiring.provider.provider_type import ProviderType, ProviderMethod


class UnknownResource(Exception):
    def __init__(self, resource: ResourceType[Any], known_modules: set[ModuleType]):
        self.resource = resource
        self.known_modules = known_modules


class ModuleAlreadyRegistered(Exception):
    def __init__(self, module: ModuleType, known_modules: set[ModuleType]):
        self.module = module
        self.known_modules = known_modules


class ProviderModuleMismatch(Exception):
    def __init__(self, provider: ProviderType, module: ModuleType):
        self.provider = provider
        self.module = module


class CannotRegisterProviderToUnknownModule(Exception):
    def __init__(self, provider: ProviderType, known_modules: set[ModuleType]):
        self.provider = provider
        self.known_modules = known_modules


class ModuleProviderAlreadyRegistered(Exception):
    def __init__(self, module: ModuleType, registering: ProviderType):
        self.module = module
        self.registering = registering


class ModuleWithoutProvider(Exception):
    def __init__(self, module: ModuleType):
        self.module = module


class CannotProvideUntilContainerIsSealed(Exception):
    pass


class CannotRegisterAfterContainerIsSealed(Exception):
    def __init__(self, registering: Union[ModuleType, ProviderType]):
        self.registering = registering


class CannotProvideRawType(Exception):
    def __init__(self, t: type):
        self.type = t


@dataclass(frozen=True)
class ResolutionStep:
    target: ResourceType[Any]
    provider_method: ProviderMethod[Any]
    parameter_name: str
    depends_on: ResourceType[Any]

    @classmethod
    def from_types(
        cls,
        target: Type[Any],
        provider_method: ProviderMethod[Any],
        parameter_name: str,
        depends_on: Type[Any],
    ) -> ResolutionStep:
        return ResolutionStep(
            target=cast(ResourceType[Any], target),
            provider_method=provider_method,
            parameter_name=parameter_name,
            depends_on=cast(ResourceType[Any], depends_on),
        )


class CircularDependency(Exception):
    def __init__(self, loop: list[ResolutionStep]):
        self.loop = loop
