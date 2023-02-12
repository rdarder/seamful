from typing import TypeAlias, cast, Any
from unittest import TestCase

from wiring.container import Container
from wiring.module import Module
from wiring.provider import Provider
from wiring.provider.errors import (
    MissingProviderMethod,
    ProviderMethodNotCallable,
    ProvidersModuleIsNotAModule,
    CannotProvideBaseModule,
    UnrelatedResource,
    ProviderMethodMissingReturnTypeAnnotation,
    ProviderMethodReturnTypeMismatch,
    ProviderMethodParameterMissingTypeAnnotation,
    ProviderMethodParameterUnrelatedName,
    ProviderMethodParameterResourceTypeMismatch,
    ProviderMethodParameterInvalidTypeAnnotation,
    ProvidersCannotBeInstantiated,
    InvalidAttributeAnnotationInProvider,
    InvalidPrivateResourceAnnotationInProvider,
    CannotDefinePublicResourceInProvider,
    PrivateResourceCannotOccludeModuleResource,
    InvalidOverridingResourceAnnotationInProvider,
    OverridingResourceIncompatibleType,
    OverridingResourceNameDoesntMatchModuleResource,
    ProviderModuleCantBeChanged,
)
from wiring.resource import (
    ModuleResource,
    Resource,
    PrivateResource,
    OverridingResource,
)


class TestProviderClassBehavior(TestCase):
    def test_providers_cannot_be_instantiated(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        with self.assertRaises(ProvidersCannotBeInstantiated) as ctx:
            SomeProvider()
        self.assertEqual(ctx.exception.provider, SomeProvider)

    def test_providers_cannot_be_instantiated_event_if_defining_constructor(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            def __init__(self) -> None:
                pass

        with self.assertRaises(ProvidersCannotBeInstantiated) as ctx:
            SomeProvider()
        self.assertEqual(ctx.exception.provider, SomeProvider)

    def test_providers_module_cannot_be_manually_set(self) -> None:
        class SomeModule(Module):
            pass

        class AnotherModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        with self.assertRaises(ProviderModuleCantBeChanged) as ctx:
            SomeProvider.module = AnotherModule

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.assigned_to, AnotherModule)
        self.assertEqual(SomeProvider.module, SomeModule)


class TestProviderCollectingProviderMethods(TestCase):
    def test_provider_collects_provider_methods(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        provider_method = SomeProvider._get_provider_method(SomeModule.a)  # type: ignore
        self.assertIs(provider_method.provider, SomeProvider)
        self.assertIs(provider_method.method, SomeProvider.provide_a)
        self.assertIs(provider_method.resource, SomeModule.a)

    def test_missing_provider_method(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(MissingProviderMethod) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_provider_method_not_callable(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodNotCallable) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                provide_a = 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_provider_method_not_found(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        fake_resource = ModuleResource.make_bound(
            t=int, name="fake", module=SomeModule  # pyright: ignore
        )
        with self.assertRaises(UnrelatedResource) as ctx:
            SomeProvider._get_provider_method(fake_resource)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, fake_resource)

    def test_provider_unrelated_resource(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = int

            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        with self.assertRaises(UnrelatedResource) as ctx:
            SomeProvider._get_provider_method(AnotherModule.a)  # type: ignore

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, AnotherModule.a)

    def test_provider_collects_methods_for_private_provider_resources(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        self.assertIsInstance(SomeProvider.a, PrivateResource)
        methods = list(SomeProvider._list_provider_methods())
        self.assertEqual(len(methods), 1)
        method = methods[0]
        self.assertEqual(method.provider, SomeProvider)
        self.assertEqual(method.method, SomeProvider.provide_a)
        self.assertEqual(method.resource, SomeProvider.a)
        self.assertEqual(method.dependencies, {})

    def test_missing_provider_method_for_private_provider_resource(self) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(MissingProviderMethod) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a: TypeAlias = int

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        resource = ctx.exception.resource
        self.assertIsInstance(resource, PrivateResource)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)

    def test_provider_collects_provider_method_when_overriden_resource_is_present(
        self,
    ) -> None:
        """
        Also, the provider method is bound to the _module_ resource, not the overriden one.
        The container will have to dereference overridden resources instead of trying to
        provide them directly.
        """

        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = Resource(SomeBaseClass)

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(SomeConcreteClass, override=True)

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        self.assertIsInstance(SomeProvider.a, OverridingResource)
        methods = list(SomeProvider._list_provider_methods())
        self.assertEqual(len(methods), 1)
        method = methods[0]
        self.assertEqual(method.provider, SomeProvider)
        self.assertEqual(method.method, SomeProvider.provide_a)
        self.assertEqual(method.resource, SomeModule.a)
        self.assertEqual(method.dependencies, {})


class TestProviderModuleAnnotation(TestCase):
    def test_invalid_provider_module_annotation(self) -> None:
        class SomeClass:
            pass

        with self.assertRaises(ProvidersModuleIsNotAModule) as ctx:

            class SomeProvider(Provider, module=SomeClass):  # pyright: ignore
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.invalid_module, SomeClass)

    def test_cannot_provide_base_module(self) -> None:
        with self.assertRaises(CannotProvideBaseModule) as ctx:

            class SomeProvider(Provider, module=Module):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")

    def test_empty_provider_provides_an_empty_module(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        self.assertEqual(SomeProvider.module, SomeModule)


class TestProviderMethodFromSignature(TestCase):
    def test_provider_method_must_have_return_type_annotation(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodMissingReturnTypeAnnotation) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self):  # type: ignore
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")

    def test_provider_method_must_have_a_compatible_return_type_annotation(
        self,
    ) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodReturnTypeMismatch) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self) -> str:
                    return "test"

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
        self.assertEqual(ctx.exception.mismatched_type, str)

    def test_provider_method_return_type_can_be_more_specific_type(self) -> None:
        class SomeBaseClass:
            pass

        class SpecificClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = SomeBaseClass

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> SpecificClass:
                return SpecificClass()

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        got = container.provide(SomeModule.a)
        self.assertIsInstance(got, SomeBaseClass)
        self.assertIsInstance(got, SpecificClass)

    def test_provider_method_parameters_must_have_type_annotations(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodParameterMissingTypeAnnotation) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self, b) -> int:  # type: ignore
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
        self.assertEqual(ctx.exception.parameter_name, "b")

    def test_provider_method_parameters_can_refer_to_module_resources(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int
            b: TypeAlias = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: SomeModule.b) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        provider_method = SomeProvider._get_provider_method(SomeModule.a)  # type: ignore
        self.assertEqual(provider_method.dependencies, dict(b=SomeModule.b))

    def test_provider_method_parameters_can_refer_to_own_module_resources_by_name(
        self,
    ) -> None:
        class SomeModule(Module):
            a = int
            b = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        provider_method = SomeProvider._get_provider_method(SomeModule.a)  # type: ignore
        self.assertEqual(provider_method.dependencies, dict(b=SomeModule.b))

    def test_provider_method_must_either_match_by_resource_or_by_name(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodParameterUnrelatedName) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self, b: int) -> int:
                    return b + 1

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
        self.assertEqual(ctx.exception.parameter_name, "b")

    def test_provider_method_referring_to_module_resource_must_match_type(self) -> None:
        class SomeModule(Module):
            a = int
            b = int

        with self.assertRaises(ProviderMethodParameterResourceTypeMismatch) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self, b: str) -> int:
                    return 10

                def provide_b(self) -> int:
                    return 11

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.parameter_name, "b")
        self.assertEqual(ctx.exception.refers_to, SomeModule.b)
        self.assertEqual(ctx.exception.mismatched_type, str)

    def test_provider_method_referring_to_module_resource_can_be_a_superclass(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = int
            b = SomeConcreteClass

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: SomeBaseClass) -> int:
                return 10

            def provide_b(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        provide_a = SomeProvider._get_provider_method(SomeModule.a)  # type: ignore
        self.assertEqual(provide_a.dependencies, dict(b=SomeModule.b))

    def test_provider_method_parameter_annotation_must_be_a_type(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodParameterInvalidTypeAnnotation) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                def provide_a(self, b: True) -> int:  # type: ignore
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
        self.assertEqual(ctx.exception.parameter_name, "b")
        self.assertEqual(ctx.exception.mismatched_type, True)

    def test_provider_method_for_binding_resource_must_satisfy_more_concrete_type(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = Resource(SomeBaseClass)

        with self.assertRaises(ProviderMethodReturnTypeMismatch) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = Resource(SomeConcreteClass, override=True)

                def provide_a(self) -> SomeBaseClass:
                    # this satisfies the module resource but not the override.
                    return SomeBaseClass()

        self.assertEqual(ctx.exception.resource.type, SomeConcreteClass)
        self.assertEqual(ctx.exception.mismatched_type, SomeBaseClass)


class TestProviderResourcesTypeAliases(TestCase):
    def test_provider_collects_private_resources_from_implicit_type_aliases(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = int

            def provide_a(self) -> int:
                return 10

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = cast(PrivateResource[Any], resources[0])
        self.assertIsInstance(resource, PrivateResource)
        self.assertIs(resource, SomeProvider.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.provider, SomeProvider)

    def test_provider_collects_overriding_resources_from_implicit_type_aliases(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = SomeBaseClass

        class SomeProvider(Provider, module=SomeModule):
            a = SomeConcreteClass

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = cast(OverridingResource[Any], resources[0])
        self.assertIsInstance(resource, OverridingResource)
        self.assertIs(resource, SomeProvider.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, SomeConcreteClass)
        self.assertEqual(resource.provider, SomeProvider)
        self.assertEqual(resource.overrides, SomeModule.a)

    def test_provider_refuses_overriding_resources_from_type_alias_if_type_not_satisfied(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = SomeBaseClass

        with self.assertRaises(OverridingResourceIncompatibleType) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = int

                def provide_a(self) -> SomeConcreteClass:
                    return SomeConcreteClass()

        resource = ctx.exception.resource
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.overrides, SomeModule.a)
        self.assertEqual(resource.name, "a")

    def test_provider_collects_resources_from_explicit_type_aliases(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeProvider.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.provider, SomeProvider)

    def test_provider_refuses_resource_from_type_alias_if_occludes_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        with self.assertRaises(PrivateResourceCannotOccludeModuleResource) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = Resource(int, private=True)

                def provide_a(self) -> int:
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource.name, "a")
        self.assertEqual(ctx.exception.resource.type, int)


class TestProviderResourcesFromResourceInstances(TestCase):
    def test_provider_collect_private_resource_instances_and_binds_them(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(int, private=True)

            def provide_a(self) -> int:
                return 10

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeProvider.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.provider, SomeProvider)

    def test_provider_collect_overriding_resource_instances_and_binds_them(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = Resource(SomeBaseClass)

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(SomeConcreteClass, override=True)

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = cast(OverridingResource[Any], resources[0])
        self.assertIs(resource, SomeProvider.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, SomeConcreteClass)
        self.assertEqual(resource.provider, SomeProvider)
        self.assertEqual(resource.overrides, SomeModule.a)

    def test_provider_fails_on_private_resource_defined_as_another_modules_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class AnotherModule(Module):
            pass

        with self.assertRaises(CannotDefinePublicResourceInProvider) as ctx:

            class SomeProvider(Provider, module=AnotherModule):
                b = SomeModule.a

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.name, "b")
        self.assertEqual(ctx.exception.type, int)

    def test_provider_refuses_definition_of_module_resource_in_it(self) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(CannotDefinePublicResourceInProvider) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = Resource(int, private=False, override=False)

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.type, int)

    def test_provider_refuses_private_resource_if_occludes_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(PrivateResourceCannotOccludeModuleResource) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = Resource(int, private=True)

                def provide_a(self) -> int:
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource.name, "a")
        self.assertEqual(ctx.exception.resource.type, int)

    def test_provider_refuses_overriding_resource_if_name_doesnt_match_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(OverridingResourceNameDoesntMatchModuleResource) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a = Resource(int, override=True)

        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.type, int)
        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.module, SomeModule)


class TestProviderResourcesFromAnnotations(TestCase):
    def test_provider_fails_on_class_attribute_with_only_type_annotation(self) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(InvalidAttributeAnnotationInProvider) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a: int

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.annotation, int)

    def test_provider_fails_on_class_attribute_annotated_with_private_resource_instance(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(InvalidPrivateResourceAnnotationInProvider) as ctx:

            class SomeProvider(Provider, module=SomeModule):
                a: Resource(int, private=True)  # type: ignore

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.is_bound, False)

    def test_provider_fails_on_class_attribute_annotated_with_overriding_resource_instance(
        self,
    ) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = Resource(SomeBaseClass)

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(SomeConcreteClass, override=True)

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        with self.assertRaises(InvalidOverridingResourceAnnotationInProvider) as ctx:

            class AnotherProvider(Provider, module=SomeModule):
                a: SomeProvider.a  # type: ignore

        self.assertEqual(ctx.exception.provider.__name__, "AnotherProvider")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.resource.type, SomeConcreteClass)
        self.assertEqual(ctx.exception.resource.is_bound, True)

    def test_provider_fails_on_a_resource_annotated_with_an_external_private_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            b = Resource(int, private=True)

            def provide_b(self) -> int:
                return 10

        with self.assertRaises(InvalidPrivateResourceAnnotationInProvider) as ctx:

            class AnotherProvider(Provider, module=SomeModule):
                c: SomeProvider.b  # type: ignore

        self.assertEqual(ctx.exception.provider.__name__, "AnotherProvider")
        self.assertEqual(ctx.exception.name, "c")
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.is_bound, True)
        self.assertEqual(ctx.exception.resource.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource.name, "b")


class TestProviderSubclasses(TestCase):
    def test_a_subclass_of_a_provider_is_also_a_provider_for_the_same_module(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        class AnotherProvider(SomeProvider):
            pass

        self.assertIs(AnotherProvider.module, SomeModule)

    def test_a_provider_subclass_collects_parent_provider_resources(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            pass

        resources = list(AnotherProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.module, SomeModule)
        self.assertEqual(resource.provider, AnotherProvider)

    def test_a_provider_subclass_doesnt_mutate_base_provider_resources(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            pass

        resources = list(SomeProvider._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.module, SomeModule)
        self.assertEqual(resource.provider, SomeProvider)

    def test_a_provider_subclass_can_add_extra_resources(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            b: TypeAlias = int

            def provide_b(self) -> int:
                return 11

        self.assertEqual(len(list(AnotherProvider._list_resources())), 2)
        self.assertEqual(len(list(AnotherProvider._list_provider_methods())), 2)
