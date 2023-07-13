from typing import Any, Optional, cast, Dict, Set, List

from seamful.application.errors import (
    ModuleWithoutRegisteredOrDefaultProvider,
    CircularDependency,
    ResolutionStep,
    RegisteredProvidersNotUsed,
)
from seamful.application.graph_provider import ModuleGraphProvider
from seamful.module.module_type import ModuleType
from seamful.provider.provider_type import ProviderType
from seamful.resource import (
    ModuleResource,
    PrivateResource,
    OverridingResource,
    BoundResource,
)


class ModuleGraphSolver:
    def __init__(
        self,
        registered_modules: Set[ModuleType],
        registered_providers: Dict[ModuleType, ProviderType],
    ):
        self._registered_modules = registered_modules

        self._providers_by_module: Dict[ModuleType, ProviderType] = {}
        self._needed_modules_without_providers: Set[ModuleType] = registered_modules.copy()
        self._unused_providers_by_module = registered_providers.copy()

    def solve(self, allow_provider_resources: bool) -> ModuleGraphProvider:
        while len(self._needed_modules_without_providers) > 0:
            for module in self._needed_modules_without_providers.copy():
                provider = self._install_provider_for_module(module)
                self._providers_by_module[module] = provider
                self._needed_modules_without_providers.remove(module)
                self._add_modules_needed_by_provider(provider)

        self._fail_on_circular_dependencies()
        self._fail_on_unused_implicit_modules()
        return ModuleGraphProvider(
            self._registered_modules,
            self._providers_by_module,
            allow_provider_resources,
        )

    def _install_provider_for_module(self, module: ModuleType) -> ProviderType:
        if module in self._unused_providers_by_module:
            return self._unused_providers_by_module.pop(module)
        elif module.default_provider is not None:
            return module.default_provider
        else:
            raise ModuleWithoutRegisteredOrDefaultProvider(module)

    def _add_modules_needed_by_provider(self, provider: ProviderType) -> None:
        for provider_method in provider:
            for parameter_name, dependency in provider_method.dependencies:
                if dependency.module not in self._providers_by_module:
                    self._needed_modules_without_providers.add(dependency.module)

    def _fail_on_circular_dependencies(self) -> None:
        solved: set[BoundResource[Any]] = set()
        loops: list[list[ResolutionStep]] = []
        for module in self._registered_modules:
            for resource in module:
                stack: set[BoundResource[Any]] = set()
                loop = self._find_circular_dependency(resource, in_stack=stack, solved=solved)
                if loop is not None:
                    loops.append(loop)
        if len(loops) > 0:
            raise CircularDependency(loops)

    def _find_circular_dependency(
        self,
        target: BoundResource[Any],
        in_stack: Set[BoundResource[Any]],
        solved: Set[BoundResource[Any]],
    ) -> Optional[List[ResolutionStep]]:
        if target in solved:
            return None
        provider = self._get_provider_for_resource(target)
        provider_method = provider[target]
        in_stack.add(target)
        if isinstance(target, OverridingResource):
            in_stack.add(target.overrides)
        for parameter_name, depends_on in provider_method.dependencies:
            if depends_on in in_stack:
                return [ResolutionStep(target, provider_method, parameter_name, depends_on)]
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

    def _get_provider_for_resource(self, resource: BoundResource[Any]) -> ProviderType:
        if isinstance(resource, (PrivateResource, OverridingResource)):
            return cast(PrivateResource[Any], resource).provider
        elif isinstance(resource, ModuleResource):
            return self._providers_by_module[resource.module]
        else:
            raise TypeError()

    def _fail_on_unused_implicit_modules(self) -> None:
        if len(self._unused_providers_by_module) > 0:
            raise RegisteredProvidersNotUsed(set(self._unused_providers_by_module.values()))
