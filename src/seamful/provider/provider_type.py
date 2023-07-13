from __future__ import annotations

import inspect
from dataclasses import dataclass
from itertools import islice
from typing import (
    Any,
    Generic,
    Iterable,
    Callable,
    TypeVar,
    TYPE_CHECKING,
    Optional,
    Iterator,
    cast,
    Type,
)

from seamful.resource import (
    ModuleResource,
    PrivateResource,
    OverridingResource,
    UnboundResource,
    BoundResource,
    ResourceKind,
    ProviderResource,
)
from seamful.provider.errors import (
    MissingProviderMethod,
    ProviderMethodNotCallable,
    ProvidersModuleIsNotAModule,
    CannotProvideBaseModule,
    ProviderMethodMissingReturnTypeAnnotation,
    ProviderMethodReturnTypeMismatch,
    ProviderMethodParameterMissingTypeAnnotation,
    ProviderMethodParameterUnrelatedName,
    ProviderMethodParameterInvalidTypeAnnotation,
    ProviderMethodParameterMatchesResourceNameButNotType,
    ProvidersCannotBeInstantiated,
    ResourceDefinitionCannotReferToExistingResource,
    CannotDefineModuleResourceInProvider,
    PrivateResourceCannotOccludeModuleResource,
    CannotDependOnResourceFromAnotherProvider,
    OverridingResourceIncompatibleType,
    OverridingResourceNameDoesntMatchModuleResource,
    ProvidersDontSupportMultipleInheritance,
    ProviderDeclarationMissingModule,
    BaseProviderProvidesFromADifferentModule,
    ProvidersMustInheritFromProviderClass,
    IncompatibleResourceTypeForInheritedResource,
    ProviderModuleCantBeChanged,
    InvalidProviderAttributeName,
    InvalidProviderAttribute,
    ResourceModuleMismatch,
    ResourceProviderMismatch,
    UnknownModuleResource,
    UnknownProviderResource,
    CannotDependOnParentProviderResource,
)

T = TypeVar("T")

if TYPE_CHECKING:
    from seamful.module.module_type import ModuleType

RESERVED_PROVIDER_ATTRIBUTES = ("module", "resources")


class ProviderType(type):
    _resources_by_name: dict[str, ProviderResource[Any]]
    _resources: set[ProviderResource[Any]]
    _provider_methods_by_resource: dict[BoundResource[Any], ProviderMethod[Any]]
    _bases: tuple[ProviderType, ...]

    def __init__(
        self,
        name: str,
        bases: tuple[ProviderType, ...],
        dct: dict[str, Any],
        *,
        module: Optional[ModuleType] = None,
    ) -> None:
        type.__init__(self, name, bases, dct)
        self._provider_methods_by_resource = {}
        self._resources_by_name = {}
        self._resources = set()
        if len(bases) == 0:
            self._bases = tuple()
            return
        if len(bases) > 1:
            raise ProvidersDontSupportMultipleInheritance(self, bases)
        base_provider = bases[0]
        self._module = self._get_module_from_class_declaration(base_provider, module)
        self._collect_resources(dct, base_provider)
        self._bases = (base_provider, *base_provider._bases)
        self._collect_provider_methods()

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ProvidersCannotBeInstantiated(self)

    def __iter__(self) -> Iterator[ProviderMethod[Any]]:
        return iter(self._provider_methods_by_resource.values())

    def __getitem__(self, resource: BoundResource[T]) -> ProviderMethod[T]:
        self._ensure_related_resource(resource)
        target_resource = (
            resource.overrides if isinstance(resource, OverridingResource) else resource
        )
        provider_method = self._provider_methods_by_resource[target_resource]
        return provider_method

    @property
    def module(self) -> ModuleType:
        return self._module

    @module.setter
    def module(self, value: Any) -> None:
        raise ProviderModuleCantBeChanged(self, value)

    @property
    def resources(
        self,
    ) -> Iterable[ProviderResource[Any]]:
        return self._resources

    def _get_module_from_class_declaration(
        self, base: type, module: Optional[ModuleType]
    ) -> ModuleType:
        from seamful.module.module_type import ModuleType, Module

        if base is Provider:
            if module is None:
                raise ProviderDeclarationMissingModule(self)
            elif module is Module:
                raise CannotProvideBaseModule(self)
            elif isinstance(module, ModuleType):
                return module
            else:
                raise ProvidersModuleIsNotAModule(self, module)
        elif issubclass(base, Provider):
            if module is not None and module is not base.module:
                raise BaseProviderProvidesFromADifferentModule(self, base, module)
            return base.module
        else:
            raise ProvidersMustInheritFromProviderClass(self, base)

    def _collect_provider_methods(self) -> None:
        for provider_resource in self._resources:
            provider_method = self._build_provider_method(provider_resource)
            self._add_provider_method(provider_method)
        for module_resource in self._module:
            if module_resource.name in self._resources_by_name:
                continue
            provider_method = self._build_provider_method(module_resource)
            self._add_provider_method(provider_method)

    def _build_provider_method(
        self,
        resource: BoundResource[T],
    ) -> ProviderMethod[T]:
        method = getattr(self, f"provide_{resource.name}", None)
        if method is None:
            raise MissingProviderMethod(resource, self)
        if not callable(method):
            raise ProviderMethodNotCallable(resource, self)
        signature = inspect.signature(method)
        if signature.return_annotation is signature.empty:
            raise ProviderMethodMissingReturnTypeAnnotation(self, resource, method)
        if not resource.is_supertype_of(signature.return_annotation):
            raise ProviderMethodReturnTypeMismatch(
                self, resource, method, mismatched_type=signature.return_annotation
            )
        method_dependencies = tuple(self._get_parameter_resources(signature, resource, method))

        bound_resource = (
            resource.overrides if isinstance(resource, OverridingResource) else resource
        )
        return ProviderMethod(
            provider=self,
            method=method,
            resource=bound_resource,
            dependencies=method_dependencies,
        )

    def _get_parameter_resources(
        self,
        signature: inspect.Signature,
        target: BoundResource[Any],
        method: Any,
    ) -> Iterable[tuple[str, BoundResource[Any]]]:
        # exclude first parameter (self)
        for name, parameter in islice(signature.parameters.items(), 1, None):
            yield name, self._get_parameter_resource(name, parameter, target, method)

    def _get_parameter_resource(
        self,
        name: str,
        parameter: inspect.Parameter,
        target: BoundResource[Any],
        method: Any,
    ) -> BoundResource[Any]:
        parameter_type: Any = parameter.annotation
        if parameter_type is inspect.Signature.empty:
            raise ProviderMethodParameterMissingTypeAnnotation(
                self, target, method, parameter_name=name
            )

        if isinstance(parameter_type, ModuleResource):
            return parameter_type

        if isinstance(parameter_type, ProviderResource):
            if parameter_type.provider in self._bases:
                raise CannotDependOnParentProviderResource(self, target, parameter_type, name)
            # when providers can be subclassed, part of this is a valid use case.
            raise CannotDependOnResourceFromAnotherProvider(self, target, parameter_type, name)

        if not isinstance(parameter_type, type):
            raise ProviderMethodParameterInvalidTypeAnnotation(
                self, target, method, name, parameter_type
            )

        # the parameter type is not a resource. We match the parameter's name with
        # the module's resource names.

        if name in self._resources_by_name:
            provider_resource = self._resources_by_name[name]
            self._ensure_parameter_type_satisfies_resource_type(
                parameter_type, provider_resource, target, name
            )
            return provider_resource
        elif name in self._module:
            module_resource = self._module[name]
            self._ensure_parameter_type_satisfies_resource_type(
                parameter_type, module_resource, target, name
            )
            return module_resource
        else:
            raise ProviderMethodParameterUnrelatedName(self, target, method, name, parameter_type)

    def _ensure_parameter_type_satisfies_resource_type(
        self,
        parameter_type: type,
        resource: BoundResource[Any],
        target: BoundResource[Any],
        parameter_name: str,
    ) -> None:
        if not resource.is_subtype_of(cast(Type[Any], parameter_type)):
            raise ProviderMethodParameterMatchesResourceNameButNotType(
                self,
                target,
                parameter_name=parameter_name,
                refers_to=resource,
                mismatched_type=parameter_type,
            )

    def _collect_resources(
        self,
        dct: dict[str, Any],
        base_provider: ProviderType,
    ) -> None:
        for name, candidate in dct.items():
            if name.startswith("_") or name.startswith("provide_"):
                continue
            resource = self._collect_resource(name, candidate)
            self._add_resource(resource)

        for base_resource in base_provider.resources:
            existing = self._resources_by_name.get(base_resource.name)
            if existing is not None:
                if not existing.is_subtype_of(base_resource.type):
                    raise IncompatibleResourceTypeForInheritedResource(
                        self,
                        existing,
                        base_provider=base_provider,
                        base_resource=base_resource,
                    )
            else:
                self._add_resource(base_resource.bound_to_sub_provider(self))

    def _collect_resource(self, name: str, candidate: Any) -> ProviderResource[Any]:
        if name in RESERVED_PROVIDER_ATTRIBUTES:
            raise InvalidProviderAttributeName(self, name, candidate, RESERVED_PROVIDER_ATTRIBUTES)
        if isinstance(candidate, UnboundResource):
            if name in self._module:
                if candidate.kind == ResourceKind.MODULE:
                    raise CannotDefineModuleResourceInProvider(self, name, candidate.type)
                elif candidate.kind == ResourceKind.PRIVATE:
                    raise PrivateResourceCannotOccludeModuleResource(self, name, candidate.type)
                return OverridingResource(candidate.type, name, self, self._module[name])
            else:
                if candidate.kind == ResourceKind.OVERRIDE:
                    raise OverridingResourceNameDoesntMatchModuleResource(
                        self, name, candidate.type
                    )
                if candidate.kind == ResourceKind.MODULE:
                    raise CannotDefineModuleResourceInProvider(self, name, candidate.type)
                return PrivateResource(candidate.type, name, self)
        elif isinstance(candidate, BoundResource):
            raise ResourceDefinitionCannotReferToExistingResource(self, name, candidate)
        elif isinstance(candidate, type):
            if name in self._module:
                overrides = self._module[name]
                overriding_resource = OverridingResource[Any](candidate, name, self, overrides)
                if not overriding_resource.is_subtype_of(overrides.type):
                    raise OverridingResourceIncompatibleType(overriding_resource, overrides)
                return overriding_resource
            else:
                return PrivateResource[Any](candidate, name, self)
        else:
            raise InvalidProviderAttribute(self, name, candidate)

    def _add_resource(self, resource: ProviderResource[Any]) -> None:
        self._resources_by_name[resource.name] = resource
        self._resources.add(resource)
        setattr(self, resource.name, resource)

    def _add_provider_method(self, provider_method: ProviderMethod[Any]) -> None:
        self._provider_methods_by_resource[provider_method.resource] = provider_method

    def _ensure_related_resource(self, resource: BoundResource[Any]) -> None:
        if isinstance(resource, ModuleResource):
            if resource.module is not self._module:
                raise ResourceModuleMismatch(self, resource)
            elif resource not in self._module:
                raise UnknownModuleResource(self, resource)
        elif isinstance(resource, (PrivateResource, OverridingResource)):
            if resource.provider is not self:
                raise ResourceProviderMismatch(self, resource)
            if resource not in self._resources:
                raise UnknownProviderResource(self, resource)
        else:
            raise TypeError()


@dataclass(frozen=True)
class ProviderMethod(Generic[T]):
    method: Callable[..., T]
    provider: ProviderType
    resource: BoundResource[Any]
    dependencies: Iterable[tuple[str, BoundResource[Any]]]


M = TypeVar("M")


class Provider(metaclass=ProviderType):
    def __init_subclass__(cls, *, module: Optional[ModuleType] = None) -> None:
        pass
