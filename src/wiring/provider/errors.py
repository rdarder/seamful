from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from wiring.errors import (
    HelpfulException,
    Text,
    qname,
    rdef,
    sname,
    point_to_definition,
)
from wiring.module.module_type import ModuleType
from wiring.resource import (
    ModuleResource,
    PrivateResource,
    OverridingResource,
    BoundResource,
    ProviderResource,
)

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType, T

fn = Callable[..., Any]


class MissingProviderMethod(HelpfulException):
    def __init__(self, resource: BoundResource[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider

    def explanation(self) -> str:
        t = Text(
            f"Provider {qname(self.provider)} provides for {qname(self.provider.module)}, "
            "but it's missing a provider method for resource:"
        )
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(f"Providers for {qname(self.provider.module)} must have a provider method ")
        t.sentence("for each of its resources.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Provider missing a provider method."


class ProviderMethodNotCallable(HelpfulException):
    def __init__(self, resource: BoundResource[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider

    def explanation(self) -> str:
        t = Text(
            f"{sname(self.provider)}.provide_{self.resource.name} looks like "
            "a provider method for"
        )
        with t.indented_block():
            t.newline(f"{rdef(self.resource)}")
        t.newline("but it's not callable.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Provider method is not callable."


class ProvidersModuleIsNotAModule(HelpfulException):
    def __init__(self, provider: ProviderType, invalid_module: Any):
        self.provider = provider
        self.invalid_module = invalid_module

    def explanation(self) -> str:
        t = Text(f"Provider {qname(self.provider)} provides for {qname(self.invalid_module)}")
        with t.indented_block():
            t.newline(
                f"class {sname(self.provider)}(Provider, module={sname(self.invalid_module)})"
            )
            t.indented_line("...")

        t.newline(f"but {qname(self.invalid_module)} is not a Module.")
        if isinstance(self.invalid_module, type):
            t.sentence(f"It's likely that you intended {qname(self.invalid_module)}")
            t.sentence("to inherit from Module")
            with t.indented_block():
                t.newline(f"class {sname(self.invalid_module)}(Module):")
                t.indented_line("...")

            t.newline(point_to_definition(self.invalid_module))
        else:
            t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider's module is not a module."


class CannotProvideBaseModule(HelpfulException):
    def __init__(self, provider: ProviderType):
        self.provider = provider

    def explanation(self) -> str:
        t = Text(f"Provider {qname(self.provider)} provides for 'Module'")
        with t.indented_block():
            t.newline(f"class {sname(self.provider)}(Provider, module=Module)")
            t.indented_line("...")

        t.newline("But Module is the base class for all Modules, not an actual module.")
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A Provider cannot provide for the base Module class. "


class ResourceModuleMismatch(HelpfulException):
    def __init__(self, provider: ProviderType, resource: ModuleResource[Any]):
        self.provider = provider
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Requested {qname(self.provider)} provider method for")
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(f"But {qname(self.provider)} provides for {qname(self.provider.module)},")
        t.sentence(f"not {qname(self.resource.module)}")
        t.blank()
        t.newline(point_to_definition(self.provider))
        t.newline(point_to_definition(self.resource.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to access a provider method for a resource from a different module "
            "than the one provided."
        )


class UnknownModuleResource(HelpfulException):
    def __init__(self, provider: ProviderType, resource: ModuleResource[Any]):
        self.provider = provider
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Requested {qname(self.provider)} provider method for")
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(f"Which appears to be a resource of {qname(self.resource.module)},")
        t.sentence("But that resource was not found.")
        t.blank()
        t.newline(point_to_definition(self.resource.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to access a provider method for an unknown module resource. "


class ResourceProviderMismatch(HelpfulException):
    def __init__(self, provider: ProviderType, resource: ProviderResource[Any]):
        self.provider = provider
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Requested {qname(self.provider)} provider method for")
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(
            f"Which belongs to {qname(self.resource.provider)}, " f"not {qname(self.provider)}."
        )
        t.blank()
        t.newline(point_to_definition(self.resource.provider))
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to access a provider method for a resource from another provider."


class UnknownProviderResource(HelpfulException):
    def __init__(self, provider: ProviderType, resource: ProviderResource[Any]):
        self.provider = provider
        self.resource = resource

    def explanation(self) -> str:
        t = Text(f"Requested {qname(self.provider)} provider method for")
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(f"Which appears to be a resource of {qname(self.provider)},")
        t.sentence("But that resource was not found.")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to access a provider method for a resource from another provider."


class ProviderMethodMissingReturnTypeAnnotation(HelpfulException):
    def __init__(self, provider: ProviderType, resource: BoundResource[Any], method: fn):
        self.provider = provider
        self.resource = resource
        self.method = method

    def explanation(self) -> str:
        t = Text(f"The provider method {sname(self.provider)}.provide_{self.resource.name}")
        t.sentence("doesn't have a return type. ")
        t.newline("All provider methods must have a return type annotation compatible with")
        t.sentence("the resource they provide for. In this case it provides for")
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(f"So the return type must be compatible with {qname(self.resource.type)}")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider method is missing a return type annotation."


class ProviderMethodReturnTypeMismatch(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        resource: BoundResource[Any],
        method: fn,
        mismatched_type: Any,
    ):
        self.provider = provider
        self.resource = resource
        self.method = method
        self.mismatched_type = mismatched_type

    def explanation(self) -> str:
        t = Text("The provider method")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.resource.name}() -> "
                f"{sname(self.mismatched_type)} "
            )
        t.sentence("provides for")
        with t.indented_block():
            t.newline(rdef(self.resource))
        t.newline(f"But the method's return type annotation {qname(self.mismatched_type)}")
        t.sentence(f"is not compatible with {qname(self.resource.type)}")

        t.newline(f"So the return type must be compatible with {qname(self.resource.type)}")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "A provider method's return type annotation is incompatible "
            "with the resource it provides."
        )


class ProviderMethodParameterMissingTypeAnnotation(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        method: fn,
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name

    def explanation(self) -> str:
        t = Text("The provider method")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}, ...) -> {sname(self.provides.type)}"
            )
        t.newline(f"is missing a type annotation for parameter {self.parameter_name}.")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider method parameter is missing a type annotation."


class ProviderMethodParameterUnrelatedName(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        method: fn,
        parameter_name: str,
        parameter_type: type,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name
        self.parameter_type = parameter_type

    def explanation(self) -> str:
        t = Text("In provider method")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {sname(self.parameter_type)}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(
            f"Parameter '{self.parameter_name}' does not refer to any resource "
            f"from {qname(self.provider)}"
        )
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            f"Parameter '{self.parameter_name}' on provider method doesn't´t refer "
            f"to any resource."
        )


class ProviderMethodParameterInvalidTypeAnnotation(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        method: fn,
        parameter_name: str,
        mismatched_type: Any,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name
        self.mismatched_type = mismatched_type

    def explanation(self) -> str:
        t = Text("In provider method")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {repr(self.mismatched_type)}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(
            f"Parameter '{self.parameter_name}' has an invalid type annotation: "
            f"{repr(self.mismatched_type)}."
        )
        t.blank()
        if self.parameter_name in self.provider.module:
            resource = self.provider.module[self.parameter_name]
            t.newline(f"Perhaps you meant {qname(resource.type)}, referring to")
            t.indented_line(rdef(resource))
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Invalid type annotation on provider method parameter."
        pass


class ProviderMethodParameterMatchesResourceNameButNotType(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        parameter_name: str,
        refers_to: BoundResource[Any],
        mismatched_type: type,
    ):
        self.provider = provider
        self.provides = provides
        self.parameter_name = parameter_name
        self.refers_to = refers_to
        self.mismatched_type = mismatched_type

    def explanation(self) -> str:
        t = Text("In provider method")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {sname(self.mismatched_type)}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(f"Parameter '{self.parameter_name}' seems to refer to the resource: ")
        with t.indented_block():
            t.newline(rdef(self.refers_to))
        t.newline("But the parameter type for")
        t.sentence(f"{self.parameter_name}: {sname(self.mismatched_type)}")
        t.sentence(f"is not compatible with the resource type: {sname(self.refers_to.type)}")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider method parameter name matches a resource, but not its type"


class ProvidersCannotBeInstantiated(HelpfulException):
    def __init__(self, provider: ProviderType):
        self.provider = provider

    def explanation(self) -> str:
        t = Text(f"Attempted to make an instance of provider {qname(self.provider)}.")
        t.newline("Providers cannot be instantiated.")
        t.sentence(
            "Instead, provider resources can be referenced directly through the " "provider class."
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Providers cannot be instantiated."


class ResourceDefinitionCannotReferToExistingResource(HelpfulException):
    def __init__(self, provider: ProviderType, name: str, resource: BoundResource[Any]):
        self.provider = provider
        self.name = name
        self.resource = resource

    def explanation(self) -> str:
        t = Text(
            f"Provider {qname(self.provider)} defines resource {self.name} as another, "
            "existing resource."
        )
        resource = self.resource
        with t.indented_block():
            t.newline(
                f"class {sname(self.provider)}" f"(Provider, module={sname(self.provider.module)}):"
            )
            t.indented_line("...")
            if isinstance(resource, ProviderResource):
                t.indented_line(f"{self.name} = {sname(resource.provider)}.{resource.name}")
            elif isinstance(resource, ModuleResource):
                t.indented_line(f"{self.name} = {sname(resource.module)}.{resource.name}")

        t.newline("But it's not a valid resource definition.")
        t.sentence("A Provider's Resource cannot be defined as an already existing Resource.")
        t.sentence("An equivalent, valid definition would be:")
        with t.indented_block():
            if isinstance(resource, ModuleResource):
                t.newline(f"{self.name} = Resource({sname(resource.type)})")
            elif isinstance(resource, PrivateResource):
                t.newline(f"{self.name} = Resource({sname(resource.type)}, ResourceKind.PRIVATE)")
            elif isinstance(resource, OverridingResource):
                t.newline(f"{self.name} = Resource({sname(resource.type)}, ResourceKind.OVERRIDE)")
            else:
                raise TypeError()

        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A Provider's Resource cannot be defined as another provider's Resource."


class CannotDefinePublicResourceInProvider(HelpfulException):
    def __init__(self, provider: ProviderType, name: str, t: type):
        self.provider = provider
        self.name = name
        self.type = t

    def explanation(self) -> str:
        t = Text(f"Provider {qname(self.provider)} defines resource {self.name} as")
        with t.indented_block():
            t.newline(f"{self.name} = Resource({sname(self.type)})")

        t.newline("But providers can only have overriding or private resources.")
        if self.name in self.provider.module:
            t.sentence("If you meant to override a module resource, you could do:")
            with t.indented_block():
                t.newline(f"{self.name} = Resource({sname(self.type)}, ResourceKind.OVERRIDE)")
        else:
            t.sentence("If you meant to define a private resource, you could do:")
            with t.indented_block():
                t.newline(f"{self.name} = Resource({sname(self.type)}, ResourceKind.PRIVATE)")

        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Unexpected module resource definition in provider."


class PrivateResourceCannotOccludeModuleResource(HelpfulException):
    def __init__(self, provider: ProviderType, name: str, t: type):
        self.provider = provider
        self.name = name
        self.type = t

    def explanation(self) -> str:
        t = Text(f"Provider {qname(self.provider)} defines resource {self.name} as")
        with t.indented_block():
            t.newline(f"{self.name} = Resource({sname(self.type)}, ResourceKind.PRIVATE)")

        t.newline(f"But {qname(self.provider)} provides for {qname(self.provider.module)},")
        t.sentence(f"which also has a resource named '{self.name}'.")
        t.sentence("Private resource names cannot occlude its module resources.")
        t.blank()
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A private provider resource is occluding its module resource with the same name"


class CannotDependOnResourceFromAnotherProvider(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        parameter_resource: ProviderResource[Any],
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.parameter_resource = parameter_resource
        self.parameter_name = parameter_name

    def explanation(self) -> str:
        t = Text("In provider method")
        resource = self.parameter_resource
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {sname(resource.provider)}.{resource.name}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(f"Parameter '{self.parameter_name}' refers to a resource from another provider")
        t.indented_line(f"{rdef(resource)}")
        t.blank()
        t.newline(
            "provider methods can only depend on other module resources, "
            "or its own provider resources."
        )
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider method cannot depend on another provider's resources."


class CannotDependOnParentProviderResource(HelpfulException):
    def __init__(
        self,
        provider: ProviderType,
        provides: BoundResource[Any],
        parameter_resource: ProviderResource[Any],
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.parameter_resource = parameter_resource
        self.parameter_name = parameter_name

    def explanation(self) -> str:
        t = Text("In provider method")
        resource = self.parameter_resource
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {sname(resource.provider)}.{resource.name}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(f"Parameter '{self.parameter_name}' is a resource from a base")
        t.sentence(f"provider {sname(resource.provider)}")
        with t.indented_block():
            t.newline(f"{rdef(resource)}")
        t.newline("Referring providers of a parent provider is not supported.")
        t.sentence(
            f"It's likely that you intended to refer to {sname(self.provider)}.{resource.name}."
        )
        t.sentence("If that's the case, you should write it as:")
        with t.indented_block():
            t.newline(
                f"{sname(self.provider)}.provide_{self.provides.name}"
                f"(..., {self.parameter_name}: {sname(resource.type)}, "
                f"...) -> {sname(self.provides.type)}"
            )
        t.newline(point_to_definition(self.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A provider method cannot depend on another provider's resources."


class OverridingResourceIncompatibleType(Exception):
    def __init__(self, resource: OverridingResource[Any]):
        self.resource = resource


class OverridingResourceNameDoesntMatchModuleResource(Exception):
    def __init__(self, provider: ProviderType, name: str, t: type):
        self.provider = provider
        self.name = name
        self.type = t


class ProvidersDontSupportMultipleInheritance(Exception):
    def __init__(self, provider: ProviderType, bases: tuple[type, ...]):
        self.provider = provider
        self.bases = bases


class ProviderDeclarationMissingModule(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class BaseProviderProvidesFromADifferentModule(Exception):
    def __init__(self, provider: ProviderType, base: ProviderType, module: ModuleType):
        self.provider = provider
        self.base = base
        self.module = module


class ProvidersMustInheritFromProviderClass(Exception):
    def __init__(self, provider: ProviderType, inherits_from: type):
        self.provider = provider
        self.inherits_from = inherits_from


class IncompatibleResourceTypeForInheritedResource(Exception):
    def __init__(
        self,
        provider: ProviderType,
        resource: ProviderResource[T],
        *,
        base_provider: ProviderType,
        base_resource: ProviderResource[T],
    ) -> None:
        self.provider = provider
        self.resource = resource
        self.base_provider = base_provider
        self.base_resource = base_resource


class ProviderModuleCantBeChanged(Exception):
    def __init__(self, provider: ProviderType, assigned_to: Any):
        self.provider = provider
        self.assigned_to = assigned_to


class InvalidProviderAttributeName(Exception):
    def __init__(self, provider: ProviderType, name: str, assigned_to: Any):
        self.provider = provider
        self.name = name
        self.assigned_to = assigned_to


class InvalidProviderAttribute(Exception):
    def __init__(self, provider: ProviderType, name: str, value: Any) -> None:
        self.provider = provider
        self.name = name
        self.value = value
