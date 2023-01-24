from typing import TypeAlias
from unittest import TestCase

from wiring.container import Container
from wiring.module import Module
from wiring.provider.provider import Provider
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
    ProviderMethodParameterResourceTypeMismatch,
    ProviderMethodParameterInvalidTypeAnnotation,
    ProvidersCannotBeInstantiated,
)
from wiring.resource import ResourceType


class TestProvider(TestCase):
    def test_providers_cannot_be_instantiated(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        with self.assertRaises(ProvidersCannotBeInstantiated) as ctx:
            SomeProvider()
        self.assertEqual(ctx.exception.provider, SomeProvider)

    def test_providers_cannot_be_instantiated_event_if_defining_constructor(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            def __init__(self) -> None:
                pass

        with self.assertRaises(ProvidersCannotBeInstantiated) as ctx:
            SomeProvider()
        self.assertEqual(ctx.exception.provider, SomeProvider)


class TestProviderCollectingProviderMethods(TestCase):
    def test_provider_collects_provider_methods(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
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

            class SomeProvider(Provider[SomeModule]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_provider_method_not_callable(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodNotCallable) as ctx:

            class SomeProvider(Provider[SomeModule]):
                provide_a = 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_provider_method_not_found(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        fake_resource = ResourceType.make_bound(
            t=int, name="fake", module=SomeModule  # pyright: ignore
        )
        with self.assertRaises(ProviderMethodNotFound) as ctx:
            SomeProvider._get_provider_method(fake_resource)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, fake_resource)

    def test_provider_unrelated_resource(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        class AnotherModule(Module):
            a = int

        with self.assertRaises(UnrelatedResource) as ctx:
            SomeProvider._get_provider_method(AnotherModule.a)  # type: ignore

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, AnotherModule.a)


class TestProviderModuleAnnotation(TestCase):
    def test_missing_provider_module_generic_annotation(self) -> None:
        with self.assertRaises(MissingProviderModuleAnnotation) as ctx:

            class SomeProvider(Provider):  # type: ignore
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")

    def test_invalid_provider_module_annotation(self) -> None:
        class SomeClass:
            pass

        with self.assertRaises(InvalidProviderModuleAnnotation) as ctx:

            class SomeProvider(Provider[SomeClass]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.invalid_module, SomeClass)

    def test_cannot_provide_base_module(self) -> None:
        with self.assertRaises(CannotProvideBaseModule) as ctx:

            class SomeProvider(Provider[Module]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")

    def test_empty_provider_provides_an_empty_module(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        self.assertEqual(SomeProvider.module, SomeModule)


class TestProviderMethodFromSignature(TestCase):
    def test_provider_method_must_have_return_type_annotation(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodMissingReturnTypeAnnotation) as ctx:

            class SomeProvider(Provider[SomeModule]):
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

            class SomeProvider(Provider[SomeModule]):
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

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> SpecificClass:
                return SpecificClass()

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        got = container.provide(SomeModule.a)
        self.assertIsInstance(got, SomeBaseClass)
        self.assertIsInstance(got, SpecificClass)

    def test_provider_method_parameters_must_have_type_annotations(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodParameterMissingTypeAnnotation) as ctx:

            class SomeProvider(Provider[SomeModule]):
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

        class SomeProvider(Provider[SomeModule]):
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

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        provider_method = SomeProvider._get_provider_method(SomeModule.a)  # type: ignore
        self.assertEqual(provider_method.dependencies, dict(b=SomeModule.b))

    def test_provider_method_must_either_match_by_resource_or_by_name(self) -> None:
        class SomeModule(Module):
            a = int

        with self.assertRaises(ProviderMethodParameterUnknownResource) as ctx:

            class SomeProvider(Provider[SomeModule]):
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

            class SomeProvider(Provider[SomeModule]):
                def provide_a(self, b: str) -> int:
                    return 10

                def provide_b(self) -> int:
                    return 11

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
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

        class SomeProvider(Provider[SomeModule]):
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

            class SomeProvider(Provider[SomeModule]):
                def provide_a(self, b: True) -> int:  # type: ignore
                    return 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.provides, SomeModule.a)
        self.assertEqual(ctx.exception.method.__name__, "provide_a")
        self.assertEqual(ctx.exception.parameter_name, "b")
        self.assertEqual(ctx.exception.mismatched_type, True)
