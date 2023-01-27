from __future__ import annotations

from typing import Any, cast, Optional, TypeVar

from wiring.container.errors import (
    ResourceModuleNotRegistered,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
    CannotRegisterProviderToNotRegisteredModule,
    CannotOverrideRegisteredProvider,
    ModuleAlreadyRegistered,
    ModuleWithoutRegisteredOrDefaultProvider,
    CircularDependency,
    ResolutionStep,
    InternalResourceModuleNotKnown,
)
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.resource import ResourceType

T = TypeVar("T")


class RegisteredProvidersNotUsed(Exception):
    def __init__(self, providers: set[ProviderType]):
        self.providers = providers


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

    def close_registration(self) -> ModuleGraphProvider:
        return ModuleGraphSolver(
            self._explicit_modules, self._explicit_providers
        ).solve()


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
        solved: set[ResourceType[Any]] = set()
        for module in self._registered_modules:
            for resource in module._list_resources():
                stack: set[ResourceType[Any]] = set()
                loop = self._find_circular_dependency(
                    resource, in_stack=stack, solved=solved
                )
                if loop is not None:
                    raise CircularDependency(loop)

    def _find_circular_dependency(
        self,
        target: ResourceType[Any],
        in_stack: set[ResourceType[Any]],
        solved: set[ResourceType[Any]],
    ) -> Optional[list[ResolutionStep]]:
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


class ModuleGraphProvider:
    def __init__(
        self,
        registered_modules: set[ModuleType],
        providers_by_module: dict[ModuleType, ProviderType],
    ):
        self._registered_modules = registered_modules
        self._providers_by_module = providers_by_module
        self._instances_by_resource: dict[ResourceType[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()

    def provide(self, resource: ResourceType[T]) -> T:
        if resource.module not in self._registered_modules:
            raise ResourceModuleNotRegistered(
                resource,
                self._registered_modules,
                set(self._providers_by_module.keys()),
            )

        return self._provide(resource)

    def _provide(self, resource: ResourceType[T]) -> T:
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        target_module = resource.module
        if target_module not in self._providers_by_module:
            raise InternalResourceModuleNotKnown(
                resource, set(self._providers_by_module.keys())
            )
        provider = self._providers_by_module[target_module]
        provider_method: ProviderMethod[T] = provider._get_provider_method(resource)
        method_parameters = {
            name: self._provide(resource)
            for name, resource in provider_method.dependencies.items()
        }
        try:
            instance = provider_method.method(
                self._fake_provider_instance, **method_parameters
            )
        except InvalidProviderInstanceAccess:
            raise ProviderMethodsCantAccessProviderInstance(
                provider, resource, provider_method
            )
        self._instances_by_resource[resource] = instance
        return instance


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
