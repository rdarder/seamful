from __future__ import annotations

import inspect
from typing import Any, Optional, TYPE_CHECKING, Iterator, cast

from wiring.module.errors import (
    DefaultProviderIsNotAProvider,
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    InvalidModuleResourceAnnotationInModule,
    InvalidAttributeAnnotationInModule,
    CannotUseExistingModuleResource,
    ModulesCannotBeInstantiated,
    InvalidPrivateResourceAnnotationInModule,
    InvalidOverridingResourceAnnotationInModule,
    CannotDefinePrivateResourceInModule,
    CannotDefineOverridingResourceInModule,
    ModulesMustInheritDirectlyFromModuleClass,
    InvalidModuleAttribute,
)
from wiring.resource import ModuleResource, PrivateResource, OverridingResource

if TYPE_CHECKING:
    from wiring.provider.provider_type import ProviderType


class ModuleType(type):
    _resources_by_name: dict[str, ModuleResource[Any]]
    _resources: set[ModuleResource[Any]]
    _default_provider: Optional[ProviderType]

    def __init__(self, name: str, bases: tuple[type, ...], dct: dict[str, Any]):
        self._resources = set()
        self._resources_by_name = {}
        self._default_provider = None
        type.__init__(self, name, bases, dct)
        if len(bases) == 0:
            return
        if bases[0] != Module:
            raise ModulesMustInheritDirectlyFromModuleClass(name, bases)
        self._collect_resources(dct)
        self._fail_on_misleading_annotations(inspect.get_annotations(self))

    def __call__(self, *args: Any, **kwargs: Any) -> None:
        raise ModulesCannotBeInstantiated(self)

    def __contains__(self, item: str | ModuleResource[Any]) -> bool:
        if type(item) is ModuleResource:
            return item in self._resources
        elif type(item) is str:
            return item in self._resources_by_name
        else:
            raise TypeError()

    def __iter__(self) -> Iterator[ModuleResource[Any]]:
        return iter(self._resources)

    def __getitem__(self, name: str) -> ModuleResource[Any]:
        return self._resources_by_name[name]

    @property
    def default_provider(self) -> Optional[ProviderType]:
        return self._default_provider

    @default_provider.setter
    def default_provider(self, provider: ProviderType) -> None:
        from wiring.provider.provider_type import Provider, ProviderType

        if not isinstance(provider, ProviderType):
            raise DefaultProviderIsNotAProvider(self, provider)
        if provider is Provider:
            raise CannotUseBaseProviderAsDefaultProvider(self)
        if provider.module is not self:
            raise DefaultProviderProvidesToAnotherModule(self, provider)
        self._default_provider = provider

    def _collect_resources(self, dct: dict[str, Any]) -> None:
        for name, candidate in dct.items():
            if name.startswith("__"):
                continue
            resource = self._turn_attribute_into_resource(name, candidate)
            self._add_resource(resource)

    def _fail_on_misleading_annotations(self, annotations: dict[str, Any]) -> None:
        for name, annotation in annotations.items():
            self._fail_on_misleading_annotation(name, annotation)

    def _fail_on_misleading_annotation(self, name: str, annotation: Any) -> None:
        if name.startswith("_") or name in self._resources_by_name:
            return
        t = type(annotation)
        if t is ModuleResource:
            raise InvalidModuleResourceAnnotationInModule(self, name, annotation)
        elif t is PrivateResource:
            raise InvalidPrivateResourceAnnotationInModule(self, name, annotation)
        elif t is OverridingResource:
            raise InvalidOverridingResourceAnnotationInModule(self, name, annotation)
        elif isinstance(annotation, type):
            raise InvalidAttributeAnnotationInModule(self, name, annotation)

    def _turn_attribute_into_resource(
        self, name: str, candidate: Any
    ) -> ModuleResource[Any]:
        if name.startswith("_") or name == "default_provider":
            raise InvalidModuleAttribute(self, name, candidate)
        candidate_type = type(candidate)
        if candidate_type is ModuleResource:
            if candidate.is_bound:
                raise CannotUseExistingModuleResource(self, name, candidate)
            candidate.bind(name=name, module=self)
            return cast(ModuleResource[Any], candidate)
        elif candidate_type is PrivateResource:
            raise CannotDefinePrivateResourceInModule(self, name, candidate.type)
        elif candidate_type is OverridingResource:
            raise CannotDefineOverridingResourceInModule(self, name, candidate.type)
        elif isinstance(candidate, type):
            resource: ModuleResource[Any] = ModuleResource.make_bound(
                t=candidate, name=name, module=self  # pyright: ignore
            )
            return resource
        else:
            raise InvalidModuleAttribute(self, name, candidate)

    def _add_resource(self, resource: ModuleResource[Any]) -> None:
        self._resources.add(resource)
        self._resources_by_name[resource.name] = resource
        setattr(self, resource.name, resource)


class Module(metaclass=ModuleType):
    pass
