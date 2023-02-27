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


class InvalidModuleResourceAnnotationInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, resource: ModuleResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")

        if self.resource.is_bound and self.resource.module is not self.module:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(
                    f"{self.name}: {sname(self.resource.module)}."
                    f"{self.resource.name}"
                )

            t.sentence(
                "It both doesn't have a value and points to another module's resource."
            )
        else:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(f"{self.name}: Resource({sname(self.resource.type)})")
            t.newline("But it has no value.")

        t.sentence("It's likely that you intended to define instead:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.resource.type)})")

        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "There's a module attribute with a type annotation of a Resource, "
            "but it's value is not a Resource."
        )


class InvalidPrivateResourceAnnotationInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, resource: PrivateResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")

        if self.resource.is_bound:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(
                    f"{self.name}: {sname(self.resource.provider)}."
                    f"{self.resource.name}"
                )

            t.sentence(
                "It both doesn't have a value and points to a provider's resource."
            )
        else:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(
                    f"{self.name}: Resource({sname(self.resource.type)}, "
                    "private=True)"
                )
            t.newline("But it has no value, plus module resources cannot be private.")

        t.sentence("It's likely that you intended to define instead:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.resource.type)})")

        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "There's a module attribute with a type annotation of a Resource, "
            "but it's value is not a Resource."
        )


class InvalidOverridingResourceAnnotationInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, resource: PrivateResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")

        if self.resource.is_bound:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(
                    f"{self.name}: {sname(self.resource.provider)}."
                    f"{self.resource.name}"
                )

            t.sentence(
                "It both doesn't have a value and points to a provider's resource."
            )
        else:
            with t.indented_block():
                t.newline(f"class {sname(self.module)}(Module):")
                t.indented_line(
                    f"{self.name}: Resource({sname(self.resource.type)}, "
                    "override=True)"
                )
            t.newline("But it has no value, plus module resources cannot be overrides.")

        t.sentence("It's likely that you intended to define instead:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.resource.type)})")

        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "There's a module attribute with a type annotation of a Resource, "
            "but it's value is not a Resource."
        )


class InvalidAttributeAnnotationInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, annotation: type):
        self.module = module
        self.name = name
        self.annotation = annotation

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name}: {sname(self.annotation)}")
        t.newline("But it has no value.")
        t.sentence("It's likely that you intended to define instead:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name}: TypeAlias = {sname(self.annotation)}")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "There's a module attribute with a type annotation of a Resource, "
            "but it's value is not a Resource."
        )


class CannotUseExistingModuleResource(HelpfulException):
    def __init__(self, module: ModuleType, name: str, resource: ModuleResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} define as an attribute '{self.name}':")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(
                f"{self.name} = {sname(self.resource.module)}.{self.resource.name}"
            )

        t.newline(
            "Which refers to another module's resource. Resources cannot be reused."
        )
        t.sentence("It's likely that you indented:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.resource.type)})")
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "A module defines a resource by assigning it to another module's resource. "
            "Module resources cannot be reused. Instead create a new one."
        )


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
