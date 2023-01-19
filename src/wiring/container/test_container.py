from typing import TypeAlias
from unittest import TestCase

from wiring.module import Module
from wiring.provider import Provider
from wiring.container import Container
from wiring.container.errors import (
    UnknownResource,
    ModuleAlreadyRegistered,
    ProviderModuleMismatch,
    CannotRegisterProviderToUnknownModule,
    ModuleProviderAlreadyRegistered,
    ModuleWithoutProvider,
    CannotProvideUntilContainerIsSealed,
    CannotRegisterAfterContainerIsSealed,
)
from wiring.resource import Resource


class TestContainerProvision(TestCase):
    def test_basic_provision(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_cant_provide_unknown_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        with self.assertRaises(UnknownResource) as ctx:
            container.provide(AnotherModule.a)

        self.assertEqual(ctx.exception.resource, AnotherModule.a)
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_container_refuses_to_provide_if_not_sealed(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotProvideUntilContainerIsSealed):
            container.provide(SomeModule.a)


class TestContainerProviderMethodDependencies(TestCase):
    def test_provider_methods_can_depend_on_resources_from_another_module(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            b: TypeAlias = int

        class AnotherProvider(Provider[AnotherModule]):
            def provide_b(self, a: SomeModule.a) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.register(AnotherModule, AnotherProvider)
        container.seal()
        self.assertEqual(container.provide(AnotherModule.b), 11)

    def test_provider_methods_can_depend_on_resources_from_the_same_module(
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

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_methods_can_depend_on_resources_from_the_same_module_via_annotation(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int
            b: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: SomeModule.b) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_methods_can_depend_on_resources_declared_as_resource_instances(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)
            b = Resource(int)

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: SomeModule.b) -> int:  # type: ignore
                # mypy doesn´t like implicit aliases, pyright types just fine.
                return b + 1  # type: ignore

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 11)  # type: ignore


class TestContainerRegistration(TestCase):
    def test_container_disallows_registering_a_module_twice(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleAlreadyRegistered) as ctx:
            container.register(SomeModule, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_container_register_provider_must_provide_for_module(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        container = Container()
        with self.assertRaises(ProviderModuleMismatch) as ctx:
            container.register(AnotherModule, SomeProvider)

        self.assertEqual(ctx.exception.provider, SomeProvider)
        self.assertEqual(ctx.exception.module, AnotherModule)
        self.assertEqual(ctx.exception.provider.module, SomeModule)

    def test_can_register_module_and_provider_independently(self) -> None:
        class SomeModule(Module):
            a = int
            pass

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule)
        container.register_provider(SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_cannot_register_provider_to_unknown_module(self) -> None:
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

    def test_cannot_register_two_providers_for_the_same_module(self) -> None:
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

    def test_cannot_register_same_provider_twice(self) -> None:
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

    def test_cant_register_module_after_container_is_sealed(self) -> None:
        class SomeModule(Module):
            pass

        container = Container()
        container.seal()
        with self.assertRaises(CannotRegisterAfterContainerIsSealed) as ctx:
            container.register(SomeModule)
        self.assertEqual(ctx.exception.registering, SomeModule)

    def test_cant_register_provider_after_container_is_sealed(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider[SomeModule]):
            pass

        container = Container()
        container.register(SomeModule)
        container.seal()
        with self.assertRaises(CannotRegisterAfterContainerIsSealed) as ctx:
            container.register_provider(AnotherProvider)
        self.assertEqual(ctx.exception.registering, AnotherProvider)


class TestDefaultProvider(TestCase):
    def test_container_cant_seal_if_a_module_lacks_a_provider(self) -> None:
        class SomeModule(Module):
            pass

        container = Container()
        container.register(SomeModule)
        with self.assertRaises(ModuleWithoutProvider) as ctx:
            container.seal()

        self.assertEqual(ctx.exception.module, SomeModule)

    def test_container_uses_default_provider_if_none_registered(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider
        container = Container()
        container.register(SomeModule)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_uses_registered_provider_over_default_provider(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 11

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_setting_default_container_after_sealing_has_no_effect(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                raise Exception("this provider was set after sealing!")

        container = Container()
        container.register(SomeModule)
        container.seal()

        SomeModule.default_provider = AnotherProvider
        self.assertEqual(container.provide(SomeModule.a), 10)
