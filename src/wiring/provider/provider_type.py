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
    cast,
    TYPE_CHECKING,
    Optional,
    Iterator,
)

from wiring.resource import (
    ModuleResource,
    PrivateResource,
    ResourceTypes,
    OverridingResource,
    ProviderResourceTypes,
)
from wiring.provider.errors import (
    MissingProviderMethod,
    ProviderMethodNotCallable,
    ProvidersModuleIsNotAModule,
    CannotProvideBaseModule,
    ProviderMethodMissingReturnTypeAnnotation,
    ProviderMethodReturnTypeMismatch,
    ProviderMethodParameterMissingTypeAnnotation,
    ProviderMethodParameterUnrelatedName,
    ProviderMethodParameterInvalidTypeAnnotation,
    ProviderMethodParameterResourceTypeMismatch,
    ProvidersCannotBeInstantiated,
    CannotUseExistingProviderResource,
    CannotDefinePublicResourceInProvider,
    InvalidAttributeAnnotationInProvider,
    InvalidPrivateResourceAnnotationInProvider,
    InvalidModuleResourceAnnotationInProvider,
    PrivateResourceCannotOccludeModuleResource,
    CannotDependOnResourceFromAnotherProvider,
    InvalidOverridingResourceAnnotationInProvider,
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
)

T = TypeVar("T")

if TYPE_CHECKING:
    from wiring.module.module_type import ModuleType


class ProviderType(type):
    _resources_by_name: dict[str, ProviderResourceTypes[Any]]
    _resources: set[ProviderResourceTypes[Any]]
    _provider_methods_by_resource: dict[ResourceTypes[Any], ProviderMethod[Any]]

    def __init__(
        self,
        name: str,
        bases: tuple[type, ...],
        dct: dict[str, Any],
        *,
        module: Optional[ModuleType] = None,
    ) -> None:
        type.__init__(self, name, bases, dct)
        self._provider_methods_by_resource = {}
        self._resources_by_name = {}
        self._resources = set()
        if len(bases) == 0:
            return
        if len(bases) > 1:
            raise ProvidersDontSupportMultipleInheritance(self, bases)
        base_provider = bases[0]
        self._module = self._get_module_from_class_declaration(base_provider, module)
        self._collect_resources(dct, cast(ProviderType, base_provider))
        self._fail_on_misleading_annotations(inspect.get_annotations(self))
        self._collect_provider_methods()

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ProvidersCannotBeInstantiated(self)

    def __iter__(self) -> Iterator[ProviderMethod[Any]]:
        return iter(self._provider_methods_by_resource.values())

    def __getitem__(self, resource: ResourceTypes[T]) -> ProviderMethod[T]:
        self._ensure_related_resource(resource)
        target_resource = (
            resource.overrides if type(resource) is OverridingResource else resource
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
    ) -> Iterable[ProviderResourceTypes[Any]]:
        return self._resources

    def _get_module_from_class_declaration(
        self, base: type, module: Optional[ModuleType]
    ) -> ModuleType:
        from wiring.module.module_type import ModuleType, Module

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
        resource: ResourceTypes[T],
    ) -> ProviderMethod[T]:
        method = getattr(self, f"provide_{resource.name}", None)
        if method is None:
            raise MissingProviderMethod(resource, self)
        if not callable(method):
            raise ProviderMethodNotCallable(resource, self)
        signature = inspect.signature(method)
        if signature.return_annotation is signature.empty:
            raise ProviderMethodMissingReturnTypeAnnotation(self, resource, method)
        if not issubclass(signature.return_annotation, resource.type):
            raise ProviderMethodReturnTypeMismatch(
                self, resource, method, mismatched_type=signature.return_annotation
            )
        method_dependencies = self._get_parameter_resources(signature, resource, method)

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
        target: ResourceTypes[Any],
        method: Any,
    ) -> dict[str, ResourceTypes[Any]]:
        method_dependencies: dict[str, ResourceTypes[Any]] = {}

        # exclude first parameter (self)
        for name, parameter in islice(signature.parameters.items(), 1, None):
            method_dependencies[name] = self._get_parameter_resource(
                name, parameter, target, method
            )

        return method_dependencies

    def _get_parameter_resource(
        self,
        name: str,
        parameter: inspect.Parameter,
        target: ResourceTypes[Any],
        method: Any,
    ) -> ResourceTypes[Any]:
        parameter_type = parameter.annotation
        if parameter_type is inspect.Signature.empty:
            raise ProviderMethodParameterMissingTypeAnnotation(
                self, target, method, parameter_name=name
            )
        if type(parameter_type) is ModuleResource:
            return parameter_type

        if type(parameter_type) is PrivateResource:
            # when providers can be subclassed, part of this is a valid use case.
            raise CannotDependOnResourceFromAnotherProvider(
                target, parameter_type, name
            )

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
            raise ProviderMethodParameterUnrelatedName(
                self, target, method, parameter_name=name
            )

    def _ensure_parameter_type_satisfies_resource_type(
        self,
        parameter_type: type,
        resource: ResourceTypes[Any],
        target: ResourceTypes[Any],
        parameter_name: str,
    ) -> None:
        if not issubclass(resource.type, parameter_type):
            raise ProviderMethodParameterResourceTypeMismatch(
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
                if not issubclass(existing.type, base_resource.type):
                    raise IncompatibleResourceTypeForInheritedResource(
                        self,
                        existing,
                        base_provider=base_provider,
                        base_resource=base_resource,
                    )
            else:
                self._add_resource(base_resource.bound_to_sub_provider(self))

    def _collect_resource(
        self, name: str, candidate: Any
    ) -> ProviderResourceTypes[Any]:
        if name == "module" or name == "resources":
            raise InvalidProviderAttributeName(self, name, candidate)
        candidate_type = type(candidate)
        if candidate_type is PrivateResource:
            if candidate.is_bound:
                raise CannotUseExistingProviderResource(self, name, candidate)
            candidate.bind(name=name, provider=self)
            if name in self._module:
                raise PrivateResourceCannotOccludeModuleResource(self, candidate)
            return cast(PrivateResource[Any], candidate)
        elif candidate_type is OverridingResource:
            if name not in self._module:
                raise OverridingResourceNameDoesntMatchModuleResource(
                    candidate.type, name, self, self._module
                )
            candidate.bind(name=name, provider=self, overrides=self._module[name])
            return cast(OverridingResource[Any], candidate)
        elif candidate_type is ModuleResource:
            raise CannotDefinePublicResourceInProvider(self, name, candidate.type)
        elif isinstance(candidate, type):
            if name in self._module:
                overrides = self._module[name]
                overriding_resource: OverridingResource[
                    Any
                ] = OverridingResource.make_bound(
                    t=candidate,  # pyright: ignore
                    name=name,
                    provider=self,
                    overrides=overrides,
                )
                if not issubclass(candidate, overrides.type):
                    raise OverridingResourceIncompatibleType(overriding_resource)
                return overriding_resource
            else:
                private_resource: PrivateResource[Any] = PrivateResource.make_bound(
                    t=candidate, name=name, provider=self  # pyright: ignore
                )
                return private_resource
        else:
            raise InvalidProviderAttribute(self, name, candidate)

    def _fail_on_misleading_annotations(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            self._fail_on_misleading_annotation(name, annotation)

    def _fail_on_misleading_annotation(self, name: str, annotation: Any) -> None:
        if name.startswith("_") or name in self._resources_by_name:
            return
        t = type(annotation)
        if t is ModuleResource:
            raise InvalidModuleResourceAnnotationInProvider(self, name, annotation)
        elif t is PrivateResource:
            raise InvalidPrivateResourceAnnotationInProvider(self, name, annotation)
        elif t is OverridingResource:
            raise InvalidOverridingResourceAnnotationInProvider(self, name, annotation)
        if isinstance(annotation, type):
            raise InvalidAttributeAnnotationInProvider(self, name, annotation)

    def _add_resource(self, resource: ProviderResourceTypes[Any]) -> None:
        self._resources_by_name[resource.name] = resource
        self._resources.add(resource)
        setattr(self, resource.name, resource)

    def _add_provider_method(self, provider_method: ProviderMethod[Any]) -> None:
        self._provider_methods_by_resource[provider_method.resource] = provider_method

    def _ensure_related_resource(self, resource: ResourceTypes[Any]) -> None:
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


@dataclass
class ProviderMethod(Generic[T]):
    method: Callable[..., T]
    provider: ProviderType
    resource: ResourceTypes[Any]
    dependencies: dict[str, ResourceTypes[Any]]


M = TypeVar("M")


class Provider(metaclass=ProviderType):
    def __init_subclass__(cls, *, module: Optional[ModuleType] = None) -> None:
        pass
