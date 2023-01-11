from __future__ import annotations

from typing import TYPE_CHECKING

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
