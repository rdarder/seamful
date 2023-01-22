from typing import TypeAlias, Sequence, Type, cast, TypeVar
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
    CannotProvideRawType,
    CircularDependency,
    ResolutionStep,
)
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.resource import Resource, ResourceType


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

    def test_cannot_provide_raw_type_even_if_signature_says_so(self) -> None:
        container = Container()
        container.seal()

        class SomeClass:
            pass

        with self.assertRaises(CannotProvideRawType) as ctx:
            container.provide(SomeClass)
        self.assertEqual(ctx.exception.type, SomeClass)


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
                return b + 1  # pyright: ignore

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.seal()
        self.assertEqual(container.provide(SomeModule.a), 11)


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


class TestCircularDependencies(TestCase):
    def test_simplest_circular_dependency_breaks_on_seal(self) -> Exception:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, a: SomeModule.a) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.seal()
        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    SomeModule.a,
                    get_provider_method(SomeProvider, SomeModule.a),
                    "a",
                    SomeModule.a,
                )
            ],
        )
        return ctx.exception

    def test_single_provider_circular_dependency_breaks_on_seal(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int
            b: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: SomeModule.b) -> int:
                return b + 1

            def provide_b(self, a: SomeModule.a) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.seal()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    SomeModule.a,
                    get_provider_method(SomeProvider, SomeModule.a),
                    "b",
                    SomeModule.b,
                ),
                ResolutionStep.from_types(
                    SomeModule.b,
                    get_provider_method(SomeProvider, SomeModule.b),
                    "a",
                    SomeModule.a,
                ),
            ],
        )
        # Circular dependencies are not returned in a deterministic order, so we are not validating
        # the error explanation with a fixture.

    def test_many_providers_circular_dependency_breaks_on_seal(self) -> None:
        class ModuleA(Module):
            a: TypeAlias = int

        class ModuleB(Module):
            b: TypeAlias = int

        class ModuleC(Module):
            c: TypeAlias = int

        class ProviderA(Provider[ModuleA]):
            def provide_a(self, param1: ModuleB.b) -> int:
                return param1 + 1

        class ProviderB(Provider[ModuleB]):
            def provide_b(self, param2: ModuleC.c) -> int:
                return param2 + 1

        class ProviderC(Provider[ModuleC]):
            def provide_c(self, param3: ModuleA.a) -> int:
                return param3 + 1

        container = Container()
        container.register(ModuleA, ProviderA)
        container.register(ModuleB, ProviderB)
        container.register(ModuleC, ProviderC)

        with self.assertRaises(CircularDependency) as ctx:
            container.seal()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    ModuleC.c,
                    get_provider_method(ProviderC, ModuleC.c),
                    "param3",
                    ModuleA.a,
                ),
                ResolutionStep.from_types(
                    ModuleA.a,
                    get_provider_method(ProviderA, ModuleA.a),
                    "param1",
                    ModuleB.b,
                ),
                ResolutionStep.from_types(
                    ModuleB.b,
                    get_provider_method(ProviderB, ModuleB.b),
                    "param2",
                    ModuleC.c,
                ),
            ],
        )

    def test_catches_inner_circular_dependency(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int
            b: TypeAlias = int
            c: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: int) -> int:
                return b

            def provide_b(self, c: int) -> int:
                return c

            def provide_c(self, b: int) -> int:
                return b

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.seal()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    SomeModule.a,
                    get_provider_method(SomeProvider, SomeModule.a),
                    "b",
                    SomeModule.b,
                ),
                ResolutionStep.from_types(
                    SomeModule.b,
                    get_provider_method(SomeProvider, SomeModule.b),
                    "c",
                    SomeModule.c,
                ),
                ResolutionStep.from_types(
                    SomeModule.c,
                    get_provider_method(SomeProvider, SomeModule.c),
                    "b",
                    SomeModule.b,
                ),
            ],
        )

    def test_providers_can_have_a_circular_module_dependency_without_a_circular_resource_dependency(
        self,
    ) -> None:
        class Module1(Module):
            a: TypeAlias = int
            c: TypeAlias = int

        class Module2(Module):
            b: TypeAlias = int
            d: TypeAlias = int

        class Provider1(Provider[Module1]):
            def provide_a(self) -> int:
                return 2

            def provide_c(self, b: Module2.b) -> int:
                return b * 5

        class Provider2(Provider[Module2]):
            def provide_b(self, a: Module1.a) -> int:
                return a * 3

            def provide_d(self, c: Module1.c) -> int:
                return c * 7

        container = Container()
        container.register(Module1, Provider1)
        container.register(Module2, Provider2)
        container.seal()
        self.assertEqual(container.provide(Module2.d), 2 * 3 * 5 * 7)

    def _assert_contains_loop(
        self, container: list[ResolutionStep], expected: Sequence[ResolutionStep]
    ) -> None:
        target_length = len(expected)
        self.assertGreater(target_length, 0)
        self.assertGreaterEqual(len(container), target_length)
        try:
            container_tip = container.index(expected[0])
        except ValueError:
            self.assertEqual(
                container, expected
            )  # this will fail regardless, but assertEqual produces a diff.
            return
        first_segment = container[container_tip : container_tip + target_length]
        remaining_elements = target_length - len(first_segment)
        second_segment = container[:remaining_elements]
        container_segment = first_segment + second_segment
        self.assertEqual(container_segment, expected)


T = TypeVar("T")


def get_provider_method(provider: ProviderType, resource: Type[T]) -> ProviderMethod[T]:
    return provider._get_provider_method(cast(ResourceType[T], resource))
