from unittest import TestCase

from .module import Module
from .provider import (
    Provider,
    MissingProviderMethod,
    ProviderMethodNotCallable,
    MissingProviderModuleAnnotation,
    InvalidProviderModuleAnnotation,
    CannotProvideBaseModule,
    UnrelatedResource,
    ProviderMethodNotFound,
)
from .resource import Resource


class TestProvider(TestCase):
    def test_provider_collects_provider_methods(self):
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        provider_method = SomeProvider._get_provider_method(SomeModule.a)
        self.assertIs(provider_method.provider, SomeProvider)
        self.assertIs(provider_method.method, SomeProvider.provide_a)
        self.assertIs(provider_method.resource, SomeModule.a)

    def test_missing_provider_method(self):
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(MissingProviderMethod) as ctx:

            class SomeProvider(Provider[SomeModule]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_provider_method_not_callable(self):
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(ProviderMethodNotCallable) as ctx:

            class SomeProvider(Provider[SomeModule]):
                provide_a = 10

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.resource, SomeModule.a)

    def test_missing_provider_module_generic_annotation(self):
        with self.assertRaises(MissingProviderModuleAnnotation) as ctx:

            class SomeProvider(Provider):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")

    def test_invalid_provider_module_annotation(self):
        class SomeClass:
            pass

        with self.assertRaises(InvalidProviderModuleAnnotation) as ctx:

            class SomeProvider(Provider[SomeClass]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")
        self.assertEqual(ctx.exception.invalid_module, SomeClass)

    def test_cannot_provide_base_module(self):
        with self.assertRaises(CannotProvideBaseModule) as ctx:

            class SomeProvider(Provider[Module]):
                pass

        self.assertEqual(ctx.exception.provider.__name__, "SomeProvider")

    def test_empty_provider_provides_an_empty_module(self):
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        self.assertEqual(SomeProvider.module, SomeModule)

    def test_provider_method_not_found(self):
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        fake_resource = Resource(int)
        fake_resource._bind("fake", SomeModule)
        with self.assertRaises(ProviderMethodNotFound) as ctx:
            SomeProvider._get_provider_method(fake_resource)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, fake_resource)

    def test_provider_unrelated_resource(self):
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        class AnotherModule(Module):
            a = Resource(int)

        with self.assertRaises(UnrelatedResource) as ctx:
            SomeProvider._get_provider_method(AnotherModule.a)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.resource, AnotherModule.a)
