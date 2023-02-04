from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from wiring.resource import (
    ModuleResource,
    PrivateResource,
    ResourceTypes,
    OverridingResource,
)

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType

fn = Callable[..., Any]


class MissingProviderMethod(Exception):
    def __init__(self, resource: ResourceTypes[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider


class ProviderMethodNotCallable(Exception):
    def __init__(self, resource: ResourceTypes[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider


class MissingProviderModuleAnnotation(Exception):
    def __init__(self, provider: ProviderType):
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
