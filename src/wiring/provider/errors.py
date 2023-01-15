from __future__ import annotations

from collections.abc import Callable
from typing import Any, TYPE_CHECKING

from wiring.resource import ResourceType

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType

fn = Callable[..., Any]


class MissingProviderMethod(Exception):
    def __init__(self, resource: ResourceType[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider


class ProviderMethodNotCallable(Exception):
    def __init__(self, resource: ResourceType[Any], provider: ProviderType):
        self.resource = resource
        self.provider = provider


class MissingProviderModuleAnnotation(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class InvalidProviderModuleAnnotation(Exception):
    def __init__(self, provider: ProviderType, invalid_module: Any):
        self.provider = provider
        self.invalid_module = invalid_module


class CannotProvideBaseModule(Exception):
    def __init__(self, provider: ProviderType):
        self.provider = provider


class ProviderMethodNotFound(Exception):
    # This means there's a problem with the implementation than a user error.
    def __init__(self, provider: ProviderType, resource: ResourceType[Any]):
        self.provider = provider
        self.resource = resource


class UnrelatedResource(Exception):
    def __init__(self, provider: ProviderType, resource: ResourceType[Any]):
        self.provider = provider
        self.resource = resource


class ProviderMethodMissingReturnTypeAnnotation(Exception):
    def __init__(self, provider: ProviderType, resource: ResourceType[Any], method: fn):
        self.provider = provider
        self.resource = resource
        self.method = method


class ProviderMethodReturnTypeMismatch(Exception):
    def __init__(
        self,
        provider: ProviderType,
        resource: ResourceType[Any],
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
        provides: ResourceType[Any],
        method: fn,
        parameter_name: str,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name


class ProviderMethodParameterUnknownResource(Exception):
    def __init__(
        self,
        provider: ProviderType,
        provides: ResourceType[Any],
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
        provides: ResourceType[Any],
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
        provides: ResourceType[Any],
        method: fn,
        parameter_name: str,
        refers_to: ResourceType[Any],
        mismatched_type: type,
    ):
        self.provider = provider
        self.provides = provides
        self.method = method
        self.parameter_name = parameter_name
        self.refers_to = refers_to
        self.mismatched_type = mismatched_type
