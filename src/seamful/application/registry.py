from __future__ import annotations
from typing import TypeVar

from seamful.application.errors import (
    ModuleAlreadyInstalled,
    CannotOverrideInstalledProvider,
)
from seamful.application.graph_provider import ModuleGraphProvider
from seamful.application.graph_solver import ModuleGraphSolver
from seamful.module.module_type import ModuleType
from seamful.provider.provider_type import ProviderType

T = TypeVar("T")


class Registry:
    def __init__(
        self, explicit_modules: set[ModuleType], explicit_providers: dict[ModuleType, ProviderType]
    ) -> None:
        self._explicit_modules = explicit_modules
        self._explicit_providers = explicit_providers

    def register_module(self, module: ModuleType) -> None:
        if module in self._explicit_modules:
            raise ModuleAlreadyInstalled(module, self._explicit_modules)

        self._explicit_modules.add(module)

    def register_provider(self, provider: ProviderType, allow_override: bool) -> None:
        module = provider.module
        installed_provider = self._explicit_providers.get(module)
        is_overriding = installed_provider is not None and installed_provider is not provider
        if is_overriding and not allow_override:
            raise CannotOverrideInstalledProvider(
                module,
                installed=self._explicit_providers[module],
                registering=provider,
            )
        self._explicit_providers[module] = provider

    def solve_graph(self, allow_provider_resources: bool) -> ModuleGraphProvider:
        return ModuleGraphSolver(self._explicit_modules, self._explicit_providers).solve(
            allow_provider_resources
        )

    def copy(self) -> Registry:
        return Registry(self._explicit_modules.copy(), self._explicit_providers.copy())

    @classmethod
    def empty(cls) -> Registry:
        return cls(set(), dict())
