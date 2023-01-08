from unittest import TestCase

from wiring.module import Module
from wiring.provider import Provider
from wiring.resource import Resource

from .container import Container

from .errors import (
    UnknownResource,
    ModuleAlreadyRegistered,
    ProviderModuleMismatch,
    CannotRegisterProviderToUnknownModule,
    ModuleProviderAlreadyRegistered,
)


class TestContainer(TestCase):
    def test_basic_provision(self):
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_cant_provide_unknown_resource(self):
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = Resource(int)

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(UnknownResource) as ctx:
            container.provide(AnotherModule.a)

        self.assertEqual(ctx.exception.resource, AnotherModule.a)
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_container_disallows_registering_a_module_twice(self):
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleAlreadyRegistered) as ctx:
            container.register(SomeModule, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_container_register_provider_must_provide_for_module(self):
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = Resource(int)

        container = Container()
        with self.assertRaises(ProviderModuleMismatch) as ctx:
            container.register(AnotherModule, SomeProvider)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.module, AnotherModule)
        self.assertEqual(ctx.exception.provider.module, SomeModule)

    def test_can_register_module_and_provider_independently(self):
        class SomeModule(Module):
            a = Resource(int)
            pass

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule)
        container.register_provider(SomeProvider)
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_cannot_register_provider_to_unknown_module(self):
        class SomeModule(Module):
            pass

        class AnotherModule(Module):
            pass

        class AnotherProvider(Provider[AnotherModule]):
            pass

        container = Container()
        container.register(SomeModule)
        with self.assertRaises(CannotRegisterProviderToUnknownModule) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_cannot_register_two_providers_for_the_same_module(self):
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        class AnotherProvider(Provider[SomeModule]):
            pass

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleProviderAlreadyRegistered) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registering, AnotherProvider)

    def test_cannot_register_same_provider_twice(self):
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleProviderAlreadyRegistered) as ctx:
            container.register_provider(SomeProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registering, SomeProvider)
