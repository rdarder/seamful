from __future__ import annotations

from typing import TYPE_CHECKING, Any

from wiring.errors import (
    Text,
    HelpfulException,
    qname,
    sname,
    point_to_definition,
)
from wiring.resource import ModuleResource, PrivateResource

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType
    from wiring.provider.provider_type import ProviderType


class DefaultProviderIsNotAProvider(HelpfulException):
    def __init__(self, module: ModuleType, not_provider: Any):
        self.module = module
        self.not_provider = not_provider

    def explanation(self) -> str:
        t = Text(
            f"Attempted to set {sname(self.module)}.default_provider = "
            f"{sname(self.not_provider)}, which is not a Provider."
        )
        t.newline(
            f"It's likely that you intended {qname(self.not_provider)} "
            "to inherit from Provider, like: "
        )

        with t.indented_block():
            t.newline(f"class {sname(self.not_provider)}(Provider):")
            t.indented_line("...")
        t.blank()
        t.newline(point_to_definition(self.not_provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to set a module's default_provider to something "
            "that's not a Provider."
        )


class CannotUseBaseProviderAsDefaultProvider(HelpfulException):
    def __init__(self, module: ModuleType):
        self.module = module

    def explanation(self) -> str:
        t = Text(
            f"Attempted to set {sname(self.module)}.default_provider = "
            f"Provider instead of a derived class."
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to set a module's default_provider to the base Provider class"
            "instead of a derived class."
        )
        pass


class DefaultProviderProvidesToAnotherModule(HelpfulException):
    def __init__(self, module: ModuleType, provider: ProviderType):
        self.module = module
        self.provider = provider

    def explanation(self) -> str:
        t = Text(
            f"Attempted to set {sname(self.module)}.default_provider = {sname(self.provider)}, "
            f"but {qname(self.provider)} provides for {qname(self.provider.module)} instead."
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to set a module's default_provider to a provider of a different module."


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


class CannotDefinePrivateResourceInModule(Exception):
    def __init__(self, module: ModuleType, name: str, t: type):
        self.module = module
        self.name = name
        self.type = t


class CannotDefineOverridingResourceInModule(Exception):
    def __init__(self, module: ModuleType, name: str, t: type):
        self.module = module
        self.name = name
        self.type = t


class ModulesMustInheritDirectlyFromModuleClass(Exception):
    def __init__(self, module_class_name: str, inherits_from: tuple[type, ...]):
        self.module_class_name = module_class_name
        self.inherits_from = inherits_from


class InvalidModuleAttribute(Exception):
    def __init__(self, module: ModuleType, name: str, attribute_value: Any):
        self.module = module
        self.name = name
        self.attribute_value = attribute_value
