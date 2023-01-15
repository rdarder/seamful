from __future__ import annotations

import inspect
from dataclasses import dataclass
from itertools import islice
from typing import Any, Generic, get_args, Iterable, Callable, Tuple, TypeVar

from wiring.module.module_type import ModuleType
from wiring.resource.resource_type import ResourceType
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
)

T = TypeVar("T")


class ProviderType(type):
    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        type.__init__(self, name, bases, dct)
        if self._is_base_provider_class(bases):
            return
        self.module = self._determine_module_from_generic_argument(dct)
        self._provider_methods_by_resource: dict[
            ResourceType[Any], ProviderMethod[Any]
        ] = {}
        self._collect_provider_methods()

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

    def _collect_provider_methods(self) -> None:
        local_resources = {
            resource.name: resource for resource in self.module._list_resources()
        }
        for resource in local_resources.values():
            provider_method = self._build_provider_method(resource, local_resources)
            self._provider_methods_by_resource[resource] = provider_method

    def _build_provider_method(
        self, resource: ResourceType[T], local_resources: dict[str, ResourceType[Any]]
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
        local_resources: dict[str, ResourceType[Any]],
        resource: ResourceType[Any],
        method: Any,
    ) -> dict[str, ResourceType[Any]]:
        method_dependencies: dict[str, ResourceType[Any]] = {}
        for name, parameter in islice(
            signature.parameters.items(), 1, None
        ):  # exclude self.
            parameter_type = parameter.annotation
            if parameter_type is signature.empty:
                raise ProviderMethodParameterMissingTypeAnnotation(
                    self, resource, method, parameter_name=name
                )
            if isinstance(parameter_type, ResourceType):
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

    def _get_provider_method(self, resource: ResourceType[T]) -> ProviderMethod[T]:
        if resource.module is not self.module:
            raise UnrelatedResource(self, resource)
        provider_method = self._provider_methods_by_resource.get(resource)
        if provider_method is None:
            # This should always be present. this would be an invalid state.
            raise ProviderMethodNotFound(self, resource)
        return provider_method

    def _list_provider_methods(self) -> Iterable[ProviderMethod[Any]]:
        return self._provider_methods_by_resource.values()


@dataclass
class ProviderMethod(Generic[T]):
    method: Callable[..., T]
    provider: ProviderType
    resource: ResourceType[Any]
    dependencies: dict[str, ResourceType[Any]]
