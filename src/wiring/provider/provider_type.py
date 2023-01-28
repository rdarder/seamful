from __future__ import annotations

import inspect
from dataclasses import dataclass
from itertools import islice
from typing import (
    Any,
    Generic,
    get_args,
    Iterable,
    Callable,
    Tuple,
    TypeVar,
)

from wiring.module.module_type import ModuleType
from wiring.resource import ModuleResource, ProviderResource
from wiring.provider.errors import (
    MissingProviderMethod,
    ProviderMethodNotCallable,
    MissingProviderModuleAnnotation,
    InvalidProviderModuleAnnotation,
    CannotProvideBaseModule,
    ProviderMethodNotFound,
    UnrelatedResource,
    ProviderMethodMissingReturnTypeAnnotation,
    ProviderMethodReturnTypeMismatch,
    ProviderMethodParameterMissingTypeAnnotation,
    ProviderMethodParameterUnknownResource,
    ProviderMethodParameterInvalidTypeAnnotation,
    ProviderMethodParameterResourceTypeMismatch,
    ProvidersCannotBeInstantiated,
    CannotUseExistingProviderResource,
    CannotDefinePublicResourceInProvider,
    InvalidAttributeAnnotationInProvider,
    InvalidProviderResourceAnnotationInProvider,
    InvalidModuleResourceAnnotationInProvider,
)

T = TypeVar("T")


class ProviderResourceCannotOccludeModuleResource(Exception):
    def __init__(self, provider: ProviderType, resource: ProviderResource[Any]):
        self.provider = provider
        self.resource = resource


class ProviderType(type):
    _resources_by_name: dict[str, ProviderResource[Any]]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        if self._is_base_provider_class(bases):
            return
        self.module = self._determine_module_from_generic_argument(dct)
        self._provider_methods_by_resource: dict[
            ModuleResource[Any], ProviderMethod[Any]
        ] = {}
        self._resources_by_name = {}
        module_resources = {
            resource.name: resource for resource in self.module._list_resources()
        }

        self._collect_provider_methods(module_resources)
        self._collect_resources(dct, inspect.get_annotations(self), module_resources)

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ProvidersCannotBeInstantiated(self)

    def _is_base_provider_class(self, bases: Tuple[type, ...]) -> bool:
        return len(bases) == 1 and bases[0] == Generic  # type: ignore
        # TODO: this is wrong

    def _determine_module_from_generic_argument(
        self, dct: dict[str, Any]
    ) -> ModuleType:
        from wiring.module import Module  # circular import
        from wiring.module.module_type import ModuleType

        bases = dct.get("__orig_bases__")
        if bases is None or len(bases) == 0:
            raise MissingProviderModuleAnnotation(self)
        generic_provider = bases[0]
        module = get_args(generic_provider)[0]
        if not isinstance(module, ModuleType):
            raise InvalidProviderModuleAnnotation(self, module)
        if module is Module:
            raise CannotProvideBaseModule(self)
        return module

    def _collect_provider_methods(
        self, module_resources: dict[str, ModuleResource[Any]]
    ) -> None:
        for resource in module_resources.values():
            provider_method = self._build_provider_method(resource, module_resources)
            self._provider_methods_by_resource[resource] = provider_method

    def _build_provider_method(
        self,
        resource: ModuleResource[T],
        local_resources: dict[str, ModuleResource[Any]],
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
        method_dependencies = self._get_parameter_resources(
            signature, local_resources, resource, method
        )

        return ProviderMethod(
            provider=self,
            method=method,
            resource=resource,
            dependencies=method_dependencies,
        )

    def _get_parameter_resources(
        self,
        signature: inspect.Signature,
        local_resources: dict[str, ModuleResource[Any]],
        resource: ModuleResource[Any],
        method: Any,
    ) -> dict[str, ModuleResource[Any]]:
        method_dependencies: dict[str, ModuleResource[Any]] = {}
        for name, parameter in islice(
            signature.parameters.items(), 1, None
        ):  # exclude self.
            parameter_type = parameter.annotation
            if parameter_type is signature.empty:
                raise ProviderMethodParameterMissingTypeAnnotation(
                    self, resource, method, parameter_name=name
                )
            if isinstance(parameter_type, ModuleResource):
                method_dependencies[name] = parameter_type
                continue

            if not isinstance(parameter_type, type):
                raise ProviderMethodParameterInvalidTypeAnnotation(
                    self, resource, method, name, parameter_type
                )

            # the parameter type is not a resource. We match the parameter's name with
            # the module's resource names.

            local_resource = local_resources.get(name)
            if local_resource is None:
                raise ProviderMethodParameterUnknownResource(
                    self, resource, method, parameter_name=name
                )

            if issubclass(local_resource.type, parameter_type):
                method_dependencies[name] = local_resource
            else:
                raise ProviderMethodParameterResourceTypeMismatch(
                    self,
                    resource,
                    method,
                    parameter_name=name,
                    refers_to=local_resource,
                    mismatched_type=parameter_type,
                )
        return method_dependencies

    def _get_provider_method(self, resource: ModuleResource[T]) -> ProviderMethod[T]:
        if resource.module is not self.module:
            raise UnrelatedResource(self, resource)
        provider_method = self._provider_methods_by_resource.get(resource)
        if provider_method is None:
            # This should always be present. this would be an invalid state.
            raise ProviderMethodNotFound(self, resource)
        return provider_method

    def _list_provider_methods(self) -> Iterable[ProviderMethod[Any]]:
        return self._provider_methods_by_resource.values()

    def _collect_resources(
        self,
        dct: dict[str, Any],
        annotations: dict[str, Any],
        module_resources: dict[str, ModuleResource[Any]],
    ) -> None:
        for name, candidate in dct.items():
            if name.startswith("_"):
                continue
            if isinstance(candidate, ProviderResource):
                if candidate.is_bound:
                    raise CannotUseExistingProviderResource(self, name, candidate)
                candidate.bind(name=name, provider=self)
                if name in module_resources:
                    raise ProviderResourceCannotOccludeModuleResource(self, candidate)
                self._resources_by_name[name] = candidate
            elif isinstance(candidate, ModuleResource):
                raise CannotDefinePublicResourceInProvider(self, name, candidate.type)
            elif isinstance(candidate, type):
                resource: ProviderResource[Any] = ProviderResource.make_bound(
                    t=candidate, name=name, provider=self  # pyright: ignore
                )
                if name in module_resources:
                    raise ProviderResourceCannotOccludeModuleResource(self, resource)
                self._resources_by_name[name] = resource
                setattr(self, name, resource)

        for name, annotation in annotations.items():
            if name.startswith("_") or name in self._resources_by_name:
                continue
            if isinstance(annotation, ModuleResource):
                raise InvalidModuleResourceAnnotationInProvider(self, name, annotation)
            if isinstance(annotation, ProviderResource):
                raise InvalidProviderResourceAnnotationInProvider(
                    self, name, annotation
                )
            if isinstance(annotation, type):
                raise InvalidAttributeAnnotationInProvider(self, name, annotation)

    def _list_resources(self) -> Iterable[ProviderResource[Any]]:
        return self._resources_by_name.values()


@dataclass
class ProviderMethod(Generic[T]):
    method: Callable[..., T]
    provider: ProviderType
    resource: ModuleResource[Any]
    dependencies: dict[str, ModuleResource[Any]]
