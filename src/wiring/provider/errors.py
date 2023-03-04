from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from wiring.errors import HelpfulException, Text, qname, rdef
from wiring.module.module_type import ModuleType
from wiring.resource import (
    ModuleResource,
    PrivateResource,
    ResourceTypes,
    OverridingResource,
    ProviderResourceTypes,
)

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType, T

fn = Callable[..., Any]


class MissingProviderMethod(HelpfulException):
    def __init__(self, resource: ResourceTypes[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider

    def explanation(self) -> str:
        t = Text(
            f"Provider {qname(self.provider)} provides for {qname(self.provider.module)}, "
            "but it's missing a provider method for resource:"
        )
        with t.indented_block():
            t.newline(rdef(self.resource))

        t.newline(
            f"Providers for {qname(self.provider.module)} must have a provider method "
        )
        t.sentence("for each of its resources.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Provider missing a provider method."


class ProviderMethodNotCallable(Exception):
    def __init__(self, resource: ResourceTypes[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider


class ProvidersModuleIsNotAModule(Exception):
    def __init__(self, provider: ProviderType, invalid_module: Any):
        self.provider = provider
        self.invalid_module = invalid_module


class CannotProvideBaseModule(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class UnrelatedResource(Exception):
    def __init__(self, provider: ProviderType, resource: ResourceTypes[Any]):
        self.provider = provider
        self.resource = resource


class ProviderMethodMissingReturnTypeAnnotation(Exception):
    def __init__(
        self, provider: ProviderType, resource: ResourceTypes[Any], method: fn
    ):
        self.provider = provider
        self.resource = resource
        self.method = method


class ProviderMethodReturnTypeMismatch(Exception):
    def __init__(
        self,
        provider: ProviderType,
        resource: ResourceTypes[Any],
        method: fn,
        mismatched_type: Any,
    ):
        self.provider = provider
        self.resource = resource
        self.method = method
        self.mismatched_type = mismatched_type


class ProviderMethodParameterMissingTypeAnnotation(Exception):
    def __init__(
        self,
        provider: ProviderType,
        provides: ResourceTypes[Any],
        method: fn,
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name


class ProviderMethodParameterUnrelatedName(Exception):
    def __init__(
        self,
        provider: ProviderType,
        provides: ResourceTypes[Any],
        method: fn,
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name


class ProviderMethodParameterInvalidTypeAnnotation(Exception):
    def __init__(
        self,
        provider: ProviderType,
        provides: ResourceTypes[Any],
        method: fn,
        parameter_name: str,
        mismatched_type: Any,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name
        self.mismatched_type = mismatched_type


class ProviderMethodParameterResourceTypeMismatch(Exception):
    def __init__(
        self,
        provider: ProviderType,
        provides: ResourceTypes[Any],
        parameter_name: str,
        refers_to: ResourceTypes[Any],
        mismatched_type: type,
    ):
        self.provider = provider
        self.provides = provides
        self.parameter_name = parameter_name
        self.refers_to = refers_to
        self.mismatched_type = mismatched_type


class ProvidersCannotBeInstantiated(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class CannotUseExistingProviderResource(Exception):
    def __init__(
        self, provider: ProviderType, name: str, resource: PrivateResource[Any]
    ):
        self.provider = provider
        self.name = name
        self.resource = resource


class CannotDefinePublicResourceInProvider(Exception):
    def __init__(self, provider: ProviderType, name: str, t: type):
        self.provider = provider
        self.name = name
        self.type = t


class InvalidModuleResourceAnnotationInProvider(Exception):
    def __init__(
        self, provider: ProviderType, name: str, resource: ModuleResource[Any]
    ):
        self.provider = provider
        self.name = name
        self.resource = resource


class InvalidPrivateResourceAnnotationInProvider(Exception):
    def __init__(
        self, provider: ProviderType, name: str, resource: PrivateResource[Any]
    ):
        self.provider = provider
        self.name = name
        self.resource = resource


class InvalidOverridingResourceAnnotationInProvider(Exception):
    def __init__(
        self, provider: ProviderType, name: str, resource: OverridingResource[Any]
    ):
        self.provider = provider
        self.name = name
        self.resource = resource


class InvalidAttributeAnnotationInProvider(Exception):
    def __init__(self, provider: ProviderType, name: str, annotation: type):
        self.provider = provider
        self.name = name
        self.annotation = annotation


class PrivateResourceCannotOccludeModuleResource(Exception):
    def __init__(self, provider: ProviderType, resource: PrivateResource[Any]):
        self.provider = provider
        self.resource = resource


class CannotDependOnResourceFromAnotherProvider(Exception):
    def __init__(
        self,
        target: ResourceTypes[Any],
        parameter_resource: PrivateResource[Any],
        parameter_name: str,
    ):
        self.target = target
        self.parameter_resource = parameter_resource
        self.parameter_name = parameter_name


class OverridingResourceIncompatibleType(Exception):
    def __init__(self, resource: OverridingResource[Any]):
        self.resource = resource


class OverridingResourceNameDoesntMatchModuleResource(Exception):
    def __init__(self, t: type, name: str, provider: ProviderType, module: ModuleType):
        self.type = t
        self.name = name
        self.provider = provider
        self.module = module


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
        resource: ProviderResourceTypes[T],
        *,
        base_provider: ProviderType,
        base_resource: ProviderResourceTypes[T],
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
