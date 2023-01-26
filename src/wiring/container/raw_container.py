from typing import Any, cast, Optional, TypeVar

from wiring.container.errors import (
    UnknownResource,
    InvalidProviderInstanceAccess,
    ProviderMethodsCantAccessProviderInstance,
    CannotRegisterProviderToUnknownModule,
    ModuleProviderAlreadyRegistered,
    ModuleAlreadyRegistered,
    ModuleWithoutProvider,
    CircularDependency,
    ResolutionStep,
)
from wiring.module.module_type import ModuleType
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.resource import ResourceType

T = TypeVar("T")


class RawContainer:
    def __init__(self) -> None:
        self._public_modules: set[ModuleType] = set()
        self._private_modules: set[ModuleType] = set()
        self._providers_by_module: dict[ModuleType, ProviderType] = {}
        self._modules_without_providers: set[ModuleType] = set()
        self._providers_yet_to_solve: set[ProviderType] = set()
        self._instances_by_resource: dict[ResourceType[Any], Any] = {}
        self._fake_provider_instance = UnusableProviderInstance()

    def provide(self, resource: ResourceType[T]) -> T:
        if resource in self._instances_by_resource:
            return cast(T, self._instances_by_resource[resource])
        target_module = resource.module
        if target_module not in self._providers_by_module:
            raise UnknownResource(resource, self._public_modules)
        provider = self._providers_by_module[target_module]
        provider_method: ProviderMethod[T] = provider._get_provider_method(resource)
        method_parameters = {
            name: self.provide(resource)
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

    def register_provider(self, provider: ProviderType) -> None:
        module = provider.module
        if module not in self._public_modules:
            raise CannotRegisterProviderToUnknownModule(provider, self._public_modules)
        if module in self._providers_by_module:
            raise ModuleProviderAlreadyRegistered(module, provider)
        self._providers_by_module[module] = provider
        self._modules_without_providers.remove(module)
        self._providers_yet_to_solve.add(provider)

    def register_public_module(self, module: ModuleType) -> None:
        if module in self._public_modules:
            raise ModuleAlreadyRegistered(module, self._public_modules)
        self._public_modules.add(module)
        self._modules_without_providers.add(module)

    def _register_private_module(self, module: ModuleType) -> None:
        self._private_modules.add(module)
        self._modules_without_providers.add(module)

    def _register_default_providers(self) -> None:
        for module in self._modules_without_providers.copy():
            provider = module.default_provider
            if provider is None:
                raise ModuleWithoutProvider(module)
            self.register_provider(provider)

    def solve_rest_of_graph(self) -> None:
        while len(self._modules_without_providers) > 0:
            self._register_default_providers()
            self._solve_providers()

        self._find_circular_dependencies()

    def _solve_providers(self) -> None:
        for provider in self._providers_yet_to_solve.copy():
            self._solve_provider(provider)

    def _solve_provider(self, provider: ProviderType) -> None:
        self._providers_yet_to_solve.remove(provider)
        for provider_method in provider._list_provider_methods():
            for parameter_name, dependency in provider_method.dependencies.items():
                module = dependency.module
                if module not in self._providers_by_module:
                    self._register_private_module(module)

    def _find_circular_dependencies(self) -> None:
        solved: set[ResourceType[Any]] = set()
        for module in self._providers_by_module.keys():
            for resource in module._list_resources():
                loop = self._find_circular_dependency(
                    resource, in_stack=set(), solved=solved
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


class UnusableProviderInstance:
    def __getattr__(self, item: str) -> Any:
        raise InvalidProviderInstanceAccess()
