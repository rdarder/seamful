from typing import TypeVar

from wiring.container.errors import (
    ModuleAlreadyRegistered,
    CannotRegisterProviderToNotRegisteredModule,
    CannotOverrideRegisteredProvider,
)
from wiring.container.graph_provider import ModuleGraphProvider
from wiring.container.graph_solver import ModuleGraphSolver
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType

T = TypeVar("T")


class Registry:
    def __init__(self) -> None:
        self._explicit_modules: set[ModuleType] = set()
        self._explicit_providers: dict[ModuleType, ProviderType] = {}

    def register_module(self, module: ModuleType) -> None:
        if module in self._explicit_modules:
            raise ModuleAlreadyRegistered(module, self._explicit_modules)

        self._explicit_modules.add(module)

    def register_provider(
        self, provider: ProviderType, allow_override: bool, allow_implicit_module: bool
    ) -> None:
        module = provider.module
        if module not in self._explicit_modules and not allow_implicit_module:
            raise CannotRegisterProviderToNotRegisteredModule(
                provider, self._explicit_modules
            )
        if module in self._explicit_providers and not allow_override:
            raise CannotOverrideRegisteredProvider(
                module,
                registered=self._explicit_providers[module],
                registering=provider,
            )
        self._explicit_providers[module] = provider

    def close_registration(self, allow_provider_resources: bool) -> ModuleGraphProvider:
        return ModuleGraphSolver(
            self._explicit_modules, self._explicit_providers
        ).solve(allow_provider_resources)
