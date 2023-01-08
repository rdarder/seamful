from wiring.module import ModuleType
from wiring.resource import Resource
from wiring.provider.provider_type import ProviderType


class UnknownResource(Exception):
    def __init__(self, resource: Resource, known_modules: set[ModuleType]):
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
