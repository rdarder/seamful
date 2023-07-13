from __future__ import annotations

from typing import TYPE_CHECKING, Any

from seamful.errors import (
    Text,
    HelpfulException,
    qname,
    sname,
    point_to_definition,
)
from seamful.resource import ModuleResource

if TYPE_CHECKING:
    from seamful.module.module_type import ModuleType
    from seamful.provider.provider_type import ProviderType


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
        return "Attempted to set a module's default_provider to something " "that's not a Provider."


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


class CannotUseExistingModuleResource(HelpfulException):
    def __init__(self, module: ModuleType, name: str, resource: ModuleResource[Any]):
        self.module = module
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines as an attribute '{self.name}':")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = {sname(self.resource.module)}.{self.resource.name}")

        t.newline("Which refers to another module's resource. Resources cannot be reused.")
        t.sentence("It's likely that you indented:")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.resource.type)})")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "A module defines a resource by assigning it to another module's resource. "
            "Module resources cannot be reused. Instead create a new one."
        )


class ModulesCannotBeInstantiated(HelpfulException):
    def __init__(self, module: ModuleType):
        self.module = module

    def explanation(self) -> str:
        t = Text(f"Attempted to make an instance of module {qname(self.module)}.")
        t.newline("Modules cannot be instantiated.")
        t.sentence(
            "Instead, module resources can be referenced directly through the " "module class."
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Modules cannot be instantiated."


class InvalidPrivateResourceInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, t: type):
        self.module = module
        self.name = name
        self.type = t

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines a private Resource.")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.type)}, ResourceKind.PRIVATE)")

        t.newline("But private resources are only meant for providers, not modules.")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Modules cannot have private resources."


class InvalidOverridingResourceInModule(HelpfulException):
    def __init__(self, module: ModuleType, name: str, t: type):
        self.module = module
        self.name = name
        self.type = t

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an overriding Resource.")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = Resource({sname(self.type)}, ResourceKind.OVERRIDE)")

        t.newline("But overriding resources are only meant for providers, not modules.")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Modules cannot have overriding resources."


class ModulesMustInheritDirectlyFromModuleClass(HelpfulException):
    def __init__(self, module_class_name: str, inherits_from: tuple[type, ...]):
        self.module_class_name = module_class_name
        self.inherits_from = inherits_from

    def explanation(self) -> str:
        from seamful.module.module_type import ModuleType

        base = self.inherits_from[0]
        t = Text(f"Module {self.module_class_name} inherits from {qname(base)}")
        with t.indented_block():
            t.newline(f"class {self.module_class_name}({sname(base)}, ...):")
            t.indented_line("...")
        t.newline("But modules must inherit directly from Module, and only from Module.")
        if isinstance(base, ModuleType):
            t.newline("Subclassing another module is not supported.")
            t.sentence(
                "Depending on your use case, you'll likely need to just use two "
                "different, orthogonal modules"
            )

        return str(t)

    def failsafe_explanation(self) -> str:
        return "Modules cannot be subclassed. All modules must inherit directly from 'Module'."


class InvalidModuleAttributeType(HelpfulException):
    def __init__(self, module: ModuleType, name: str, attribute_value: Any):
        self.module = module
        self.name = name
        self.attribute_value = attribute_value

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = {repr(self.attribute_value)}")

        t.newline(f"But {repr(self.attribute_value)} is not a valid resource type.")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Invalid module attribute type. All module attributes must be Resources"


class InvalidPrivateModuleAttribute(HelpfulException):
    def __init__(self, module: ModuleType, name: str, attribute_value: Any):
        self.module = module
        self.name = name
        self.attribute_value = attribute_value

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = ...")

        t.newline("But private attributes (starting with '_') are not supported.")
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Private attributes in modules are not supported."


class InvalidModuleAttributeName(HelpfulException):
    def __init__(self, module: ModuleType, name: str, attribute_value: Any):
        self.module = module
        self.name = name
        self.attribute_value = attribute_value

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} defines an attribute '{self.name}'")
        with t.indented_block():
            t.newline(f"class {sname(self.module)}(Module):")
            t.indented_line(f"{self.name} = ...")

        t.newline(
            f"But the name '{self.name}' is reserved and cannot be used for "
            "defining a module resource."
        )
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return f"Attribute name {self.name} cannot be used in a module definition"
