from typing import Any, Optional

from wiring.container.errors import (
    ModuleWithoutRegisteredOrDefaultProvider,
    CircularDependency,
    ResolutionStep,
    RegisteredProvidersNotUsed,
)
from wiring.container.graph_provider import ModuleGraphProvider
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType
from wiring.resource import ModuleResource, ResourceTypes


class ModuleGraphSolver:
    def __init__(
        self,
        registered_modules: set[ModuleType],
        registered_providers: dict[ModuleType, ProviderType],
    ):
        self._registered_modules = registered_modules

        self._providers_by_module: dict[ModuleType, ProviderType] = {}
        self._needed_modules_without_providers: set[
            ModuleType
        ] = registered_modules.copy()
        self._unused_providers_by_module = registered_providers.copy()

    def solve(self) -> ModuleGraphProvider:
        while len(self._needed_modules_without_providers) > 0:
            for module in self._needed_modules_without_providers.copy():
                provider = self._use_provider_for_module(module)
                self._providers_by_module[module] = provider
                self._needed_modules_without_providers.remove(module)
                self._add_modules_needed_by_provider(provider)

        self._fail_on_circular_dependencies()
        self._fail_on_unused_implicit_modules()
        return ModuleGraphProvider(self._registered_modules, self._providers_by_module)

    def _use_provider_for_module(self, module: ModuleType) -> ProviderType:
        if module in self._unused_providers_by_module:
            return self._unused_providers_by_module.pop(module)
        elif module.default_provider is not None:
            return module.default_provider
        else:
            raise ModuleWithoutRegisteredOrDefaultProvider(module)

    def _add_modules_needed_by_provider(self, provider: ProviderType) -> None:
        for provider_method in provider._list_provider_methods():
            for parameter_name, dependency in provider_method.dependencies.items():
                if dependency.module not in self._providers_by_module:
                    self._needed_modules_without_providers.add(dependency.module)

    def _fail_on_circular_dependencies(self) -> None:
        solved: set[ResourceTypes[Any]] = set()
        for module in self._registered_modules:
            for resource in module._list_resources():
                stack: set[ResourceTypes[Any]] = set()
                loop = self._find_circular_dependency(
                    resource, in_stack=stack, solved=solved
                )
                if loop is not None:
                    raise CircularDependency(loop)

    def _find_circular_dependency(
        self,
        target: ResourceTypes[Any],
        in_stack: set[ResourceTypes[Any]],
        solved: set[ResourceTypes[Any]],
    ) -> Optional[list[ResolutionStep]]:
        if not isinstance(target, ModuleResource):
            raise NotImplementedError()
        if target in solved:
            return None
        provider = self._providers_by_module[target.module]
        provider_method = provider._get_provider_method(target)
        in_stack.add(target)
        for parameter_name, depends_on in provider_method.dependencies.items():
            if depends_on in in_stack:
                return [
                    ResolutionStep(target, provider_method, parameter_name, depends_on)
                ]
            loop = self._find_circular_dependency(depends_on, in_stack, solved)
            if loop is not None:
                loop.insert(
                    0,
                    ResolutionStep(target, provider_method, parameter_name, depends_on),
                )
                return loop
        in_stack.remove(target)
        solved.add(target)
        return None

    def _fail_on_unused_implicit_modules(self) -> None:
        if len(self._unused_providers_by_module) > 0:
            raise RegisteredProvidersNotUsed(
                set(self._unused_providers_by_module.values())
            )
