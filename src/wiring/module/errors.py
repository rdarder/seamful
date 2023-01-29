from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wiring.resource import ModuleResource, PrivateResource

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType
    from wiring.provider.provider_type import ProviderType


class DefaultProviderIsNotAProvider(Exception):
    def __init__(self, module: ModuleType, not_provider: ProviderType):
        self.module = module
        self.not_provider = not_provider


class CannotUseBaseProviderAsDefaultProvider(Exception):
    def __init__(self, module: ModuleType):
        self.module = module


class DefaultProviderProvidesToAnotherModule(Exception):
    def __init__(self, module: ModuleType, provider: ProviderType):
        self.module = module
        self.provider = provider


class InvalidModuleResourceAnnotationInModule(Exception):
    def __init__(self, module: ModuleType, name: str, resource: ModuleResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource


class InvalidPrivateResourceAnnotationInModule(Exception):
    def __init__(self, module: ModuleType, name: str, resource: PrivateResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource


class InvalidOverridingResourceAnnotationInModule(Exception):
    def __init__(self, module: ModuleType, name: str, resource: PrivateResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource


class InvalidAttributeAnnotationInModule(Exception):
    def __init__(self, module: ModuleType, name: str, annotation: type):
        self.module = module
        self.name = name
        self.annotation = annotation


class CannotUseExistingModuleResource(Exception):
    def __init__(self, module: ModuleType, name: str, resource: ModuleResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource


class ModulesCannotBeInstantiated(Exception):
    def __init__(self, module: ModuleType):
        self.module = module
