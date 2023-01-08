from unittest import TestCase

from wiring.module import Module
from wiring.provider import Provider
from wiring.resource import Resource

from .container import (
    Container,
    UnknownResource,
    ModuleAlreadyRegistered,
    ProviderModuleMismatch,
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
