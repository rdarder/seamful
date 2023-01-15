from typing import Union, Any

from wiring.module.module_type import ModuleType
from wiring.resource.resource_type import ResourceType
from wiring.provider.provider_type import ProviderType


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
