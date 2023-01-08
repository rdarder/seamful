from __future__ import annotations
from typing import Any, TYPE_CHECKING

from wiring.resource import ResourceType

if TYPE_CHECKING:
    from .provider_type import ProviderType


class MissingProviderMethod(Exception):
    def __init__(self, resource: ResourceType, provider: ProviderType):
        self.resource = resource
        self.provider = provider


class ProviderMethodNotCallable(Exception):
    def __init__(self, resource: ResourceType, provider: ProviderType):
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
    def __init__(self, provider: ProviderType, resource: ResourceType):
        self.provider = provider
        self.resource = resource


class UnrelatedResource(Exception):
    def __init__(self, provider: ProviderType, resource: ResourceType):
        self.provider = provider
        self.resource = resource
