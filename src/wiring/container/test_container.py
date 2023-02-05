from typing import TypeAlias, Sequence, Type, cast, TypeVar
from unittest import TestCase

from wiring.module import Module
from wiring.provider import Provider
from wiring.container import Container
from wiring.container.errors import (
    ModuleNotRegisteredForResource,
    ModuleAlreadyRegistered,
    ProviderModuleMismatch,
    CannotRegisterProviderToNotRegisteredModule,
    CannotOverrideRegisteredProvider,
    ModuleWithoutRegisteredOrDefaultProvider,
    CannotProvideUntilRegistrationsAreClosed,
    RegistrationsAreClosed,
    CannotProvideRawType,
    CircularDependency,
    ResolutionStep,
    ProviderMethodsCantAccessProviderInstance,
    CannotReopenRegistrationsAfterHavingProvidedResources,
    RegisteredProvidersNotUsed,
)
from wiring.provider.provider_type import ProviderType, ProviderMethod
from wiring.provider.errors import CannotDependOnResourceFromAnotherProvider
from wiring.resource import Resource, ModuleResource


class TestContainerProvision(TestCase):
    def test_basic_provision(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_provides_singletons_per_resource(self) -> None:
        class SomeClass:
            pass

        class SomeModule(Module):
            a: TypeAlias = SomeClass

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> SomeClass:
                return SomeClass()

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        first = container.provide(SomeModule.a)
        second = container.provide(SomeModule.a)
        self.assertIs(first, second)
        self.assertIsInstance(first, SomeClass)

    def test_container_provides_singletons_per_resource_even_when_indirectly_generated(
        self,
    ) -> None:
        class Storage:
            pass

        class SomeService:
            def __init__(self, storage: Storage):
                self.storage = storage

        class SomeModule(Module):
            storage: TypeAlias = Storage
            service: TypeAlias = SomeService

        class SomeProvider(Provider[SomeModule]):
            def provide_storage(self) -> Storage:
                return Storage()

            def provide_service(self, storage: Storage) -> SomeService:
                return SomeService(storage)

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        service = container.provide(SomeModule.service)
        storage = container.provide(SomeModule.storage)
        self.assertIs(service.storage, storage)
        self.assertIsInstance(storage, Storage)

    def test_container_cant_provide_unknown_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        with self.assertRaises(ModuleNotRegisteredForResource) as ctx:
            container.provide(AnotherModule.a)

        self.assertEqual(ctx.exception.resource, AnotherModule.a)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})
        self.assertEqual(ctx.exception.known_modules, {SomeModule})

    def test_container_refuses_to_provide_before_registrations_are_closed(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotProvideUntilRegistrationsAreClosed):
            container.provide(SomeModule.a)

    def test_cannot_provide_raw_type_even_if_signature_says_so(self) -> None:
        container = Container.empty()
        container.close_registrations()

        class SomeClass:
            pass

        with self.assertRaises(CannotProvideRawType) as ctx:
            container.provide(SomeClass)
        self.assertEqual(ctx.exception.type, SomeClass)


class TestContainerProvidesPrivateResources(TestCase):
    def test_can_provide_private_resource(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            a: TypeAlias = int

            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations(allow_provider_resources=True)
        self.assertEqual(container.provide(SomeProvider.a), 10)

    def test_provider_method_can_depend_on_private_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_method_cannot_depend_on_another_providers_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            b: TypeAlias = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        class AnotherModule(Module):
            c = int

        with self.assertRaises(CannotDependOnResourceFromAnotherProvider) as ctx:

            class AnotherProvider(Provider[AnotherModule]):
                def provide_c(self, b: SomeProvider.b) -> int:
                    return b + 1

        self.assertEqual(ctx.exception.parameter_resource, SomeProvider.b)
        self.assertEqual(ctx.exception.parameter_name, "b")
        self.assertEqual(ctx.exception.target, AnotherModule.c)


class TestContainerProvidesOverridingResources(TestCase):
    def test_can_provide_overriding_resource(self) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a: TypeAlias = SomeBaseClass

        class SomeProvider(Provider[SomeModule]):
            a: TypeAlias = SomeConcreteClass

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations(allow_provider_resources=True)

        from_overriden = container.provide(SomeProvider.a)
        self.assertIsInstance(from_overriden, SomeConcreteClass)
        from_module = container.provide(SomeModule.a)
        self.assertIs(from_overriden, from_module)

    def test_provider_method_can_depend_on_private_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_method_can_depend_on_overriding_resource(self) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class AnotherClass:
            def __init__(self, some: SomeConcreteClass):
                self.some = some

        class SomeModule(Module):
            some: TypeAlias = SomeBaseClass
            another: TypeAlias = AnotherClass

        class SomeProvider(Provider[SomeModule]):
            some: TypeAlias = SomeConcreteClass

            def provide_some(self) -> SomeConcreteClass:
                return SomeConcreteClass()

            def provide_another(self, some: SomeConcreteClass) -> AnotherClass:
                return AnotherClass(some)

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()

        another = container.provide(SomeModule.another)
        self.assertIsInstance(another, AnotherClass)
        some = container.provide(SomeModule.some)
        self.assertIsInstance(some, SomeConcreteClass)
        self.assertIs(another.some, some)

    def test_provider_method_cannot_depend_on_another_providers_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            b: TypeAlias = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        class AnotherModule(Module):
            c = int

        with self.assertRaises(CannotDependOnResourceFromAnotherProvider) as ctx:

            class AnotherProvider(Provider[AnotherModule]):
                def provide_c(self, b: SomeProvider.b) -> int:
                    return b + 1

        self.assertEqual(ctx.exception.parameter_resource, SomeProvider.b)
        self.assertEqual(ctx.exception.parameter_name, "b")
        self.assertEqual(ctx.exception.target, AnotherModule.c)


class TestContainerCallingProviderMethods(TestCase):
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.register(AnotherModule, AnotherProvider)
        container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_method_cannot_access_the_provider_instance(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class ProviderAssumingInstanceIsAvailable(Provider[SomeModule]):
            def provide_a(self) -> int:
                if getattr(self, "cache", None) is None:
                    setattr(self, "cache", 10)
                return self.cache  # type: ignore

        container = Container.empty()
        container.register(SomeModule, ProviderAssumingInstanceIsAvailable)
        container.close_registrations()
        with self.assertRaises(ProviderMethodsCantAccessProviderInstance) as ctx:
            container.provide(SomeModule.a)

        self.assertEqual(ctx.exception.resource, SomeModule.a)
        self.assertEqual(
            ctx.exception.provider_method,
            get_provider_method(ProviderAssumingInstanceIsAvailable, SomeModule.a),
        )


class TestContainerRegistration(TestCase):
    def test_container_disallows_registering_a_module_twice(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleAlreadyRegistered) as ctx:
            container.register(SomeModule, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})

    def test_container_register_provider_must_provide_for_module(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        container = Container.empty()
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

        container = Container.empty()
        container.register(SomeModule)
        container.register_provider(SomeProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_cannot_register_provider_to_unknown_module(self) -> None:
        class SomeModule(Module):
            pass

        class AnotherModule(Module):
            pass

        class AnotherProvider(Provider[AnotherModule]):
            pass

        container = Container.empty()
        container.register(SomeModule)
        with self.assertRaises(CannotRegisterProviderToNotRegisteredModule) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})

    def test_cannot_register_two_providers_for_the_same_module(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        class AnotherProvider(Provider[SomeModule]):
            pass

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.registering, AnotherProvider)

    def test_cannot_register_same_provider_twice(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(SomeProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.registering, SomeProvider)

    def test_cant_register_module_after_registrations_are_closed(self) -> None:
        class SomeModule(Module):
            pass

        container = Container.empty()
        container.close_registrations()
        with self.assertRaises(RegistrationsAreClosed) as ctx:
            container.register(SomeModule)
        self.assertEqual(ctx.exception.registering, SomeModule)

    def test_cant_register_provider_after_registrations_are_closed(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider[SomeModule]):
            pass

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider[SomeModule]):
            pass

        container = Container.empty()
        container.register(SomeModule)
        container.close_registrations()
        with self.assertRaises(RegistrationsAreClosed) as ctx:
            container.register_provider(AnotherProvider)
        self.assertEqual(ctx.exception.registering, AnotherProvider)


class TestContainerOverrides(TestCase):
    def test_can_override_a_provider_when_reopening_for_registration(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        container.reopen_registrations(allow_overrides=True)

        class AnotherProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_can_override_a_default_provider_when_reopening_for_registration(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        container = Container.empty()
        container.register(SomeModule)
        container.close_registrations()
        container.reopen_registrations(allow_overrides=True)

        class AnotherProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.close_registrations()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_cannot_reopen_for_registration_once_a_resource_has_been_provided(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        container.provide(SomeModule.a)
        with self.assertRaises(CannotReopenRegistrationsAfterHavingProvidedResources):
            container.reopen_registrations()

    def test_cannot_override_reopened_container_if_overrides_are_not_explicitly_allowed(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.close_registrations()
        container.reopen_registrations()

        class AnotherProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 11

        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registering, AnotherProvider)


class TestContainerImplicitProviders(TestCase):
    def test_cant_register_implicit_provider(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class AnotherModule(Module):
            b: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, b: AnotherModule.b) -> int:
                return b + 1

        class AnotherProvider(Provider[AnotherModule]):
            def provide_b(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotRegisterProviderToNotRegisteredModule) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})

    def test_can_register_implicit_provider_if_reopened_explicitly_and_module_is_used(
        self,
    ) -> None:
        class Module1(Module):
            a: TypeAlias = int

        class Module2(Module):
            b: TypeAlias = int

        class Provider1(Provider[Module1]):
            def provide_a(self, b: Module2.b) -> int:
                return b + 1

        class Provider2(Provider[Module2]):
            def provide_b(self) -> int:
                return 10

        Module2.default_provider = Provider2

        class AnotherProvider2(Provider[Module2]):
            def provide_b(self) -> int:
                return 11

        container = Container.empty()
        container.register(Module1, Provider1)
        container.close_registrations()
        container.reopen_registrations(
            allow_overrides=True, allow_implicit_modules=True
        )
        container.register_provider(AnotherProvider2)
        container.close_registrations()
        self.assertEqual(container.provide(Module1.a), 12)

    def test_container_fails_on_closing_registration_if_any_implicit_provider_is_unused(
        self,
    ) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.close_registrations()
        container.reopen_registrations(
            allow_overrides=True, allow_implicit_modules=True
        )
        container.register_provider(SomeProvider)
        with self.assertRaises(RegisteredProvidersNotUsed) as ctx:
            container.close_registrations()
        self.assertEqual(ctx.exception.providers, {SomeProvider})


class TestDefaultProvider(TestCase):
    def test_container_cant_seal_if_a_module_lacks_a_provider(self) -> None:
        class SomeModule(Module):
            pass

        container = Container.empty()
        container.register(SomeModule)
        with self.assertRaises(ModuleWithoutRegisteredOrDefaultProvider) as ctx:
            container.close_registrations()

        self.assertEqual(ctx.exception.module, SomeModule)

    def test_container_uses_default_provider_if_none_registered(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider
        container = Container.empty()
        container.register(SomeModule)
        container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule, AnotherProvider)
        container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule)
        container.close_registrations()

        SomeModule.default_provider = AnotherProvider
        self.assertEqual(container.provide(SomeModule.a), 10)


class TestCircularDependencies(TestCase):
    def test_simplest_circular_dependency_breaks_on_seal(self) -> Exception:
        class SomeModule(Module):
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            def provide_a(self, a: SomeModule.a) -> int:
                return a + 1

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()

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

        container = Container.empty()
        container.register(ModuleA, ProviderA)
        container.register(ModuleB, ProviderB)
        container.register(ModuleC, ProviderC)

        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()

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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
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

    def test_catches_circular_dependencies_involving_private_resources(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider[SomeModule]):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self, a: int) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    SomeModule.a,
                    get_provider_method(SomeProvider, SomeModule.a),
                    "b",
                    SomeProvider.b,
                ),
                ResolutionStep.from_types(
                    SomeProvider.b,
                    get_provider_method(SomeProvider, SomeProvider.b),
                    "a",
                    SomeModule.a,
                ),
            ],
        )

    def test_catches_circular_dependencies_involving_overriding_resources(self) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            def __init__(self, param: int):
                self.param = param

        class SomeModule(Module):
            some: TypeAlias = SomeBaseClass
            a: TypeAlias = int

        class SomeProvider(Provider[SomeModule]):
            some: TypeAlias = SomeConcreteClass
            private: TypeAlias = int

            def provide_a(self, some: SomeConcreteClass) -> int:
                return some.param

            def provide_some(self, private: int) -> SomeConcreteClass:
                return SomeConcreteClass(private)

            def provide_private(self, a: int) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.close_registrations()

        self._assert_contains_loop(
            ctx.exception.loop,
            [
                ResolutionStep.from_types(
                    SomeProvider.private,
                    get_provider_method(SomeProvider, SomeProvider.private),
                    "a",
                    SomeModule.a,
                ),
                ResolutionStep.from_types(
                    SomeModule.a,
                    get_provider_method(SomeProvider, SomeModule.a),
                    "some",
                    SomeProvider.some,
                ),
                ResolutionStep.from_types(
                    SomeProvider.some,
                    get_provider_method(SomeProvider, SomeModule.some),
                    "private",
                    SomeProvider.private,
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

        container = Container.empty()
        container.register(Module1, Provider1)
        container.register(Module2, Provider2)
        container.close_registrations()
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
                expected, container
            )  # this will fail regardless, but assertEqual produces a diff.
            return
        first_segment = container[container_tip : container_tip + target_length]
        remaining_elements = target_length - len(first_segment)
        second_segment = container[:remaining_elements]
        container_segment = first_segment + second_segment
        self.assertEqual(expected, container_segment)


T = TypeVar("T")


def get_provider_method(provider: ProviderType, resource: Type[T]) -> ProviderMethod[T]:
    return provider._get_provider_method(cast(ModuleResource[T], resource))
