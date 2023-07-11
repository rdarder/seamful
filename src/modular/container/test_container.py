from typing import Sequence, Type, cast, TypeVar, List

from modular.errors import HelpfulException
from modular.module import Module
from modular.container import Container
from modular.container.errors import (
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
    CannotTamperAfterHavingProvidedResources,
    RegisteredProvidersNotUsed,
    CannotTamperUntilContainerIsReady,
    ContainerAlreadyReady,
    ProviderResourceOfUnregisteredProvider,
    CannotTamperWithContainerTwice,
    ContainerWasNotTamperedWith,
)
from modular.provider.provider_type import Provider, ProviderType, ProviderMethod
from modular.resource import Resource, ModuleResource
from modular.utils_for_tests import (
    validate_output,
    TestCaseWithOutputFixtures,
    validate_output_any_line_order,
)


class TestContainerProvision(TestCaseWithOutputFixtures):
    def test_basic_provision(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_provides_singletons_per_resource(self) -> None:
        class SomeClass:
            pass

        class SomeModule(Module):
            a = Resource(SomeClass)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> SomeClass:
                return SomeClass()

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
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
            storage = Resource(Storage)
            service = Resource(SomeService)

        class SomeProvider(Provider, module=SomeModule):
            def provide_storage(self) -> Storage:
                return Storage()

            def provide_service(self, storage: Storage) -> SomeService:
                return SomeService(storage)

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        service = container.provide(SomeModule.service)
        storage = container.provide(SomeModule.storage)
        self.assertIs(service.storage, storage)
        self.assertIsInstance(storage, Storage)

    @validate_output
    def test_container_cant_provide_unknown_resource(self) -> HelpfulException:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            a = int

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        with self.assertRaises(ModuleNotRegisteredForResource) as ctx:
            container.provide(AnotherModule.a)

        self.assertEqual(ctx.exception.resource, AnotherModule.a)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})
        self.assertEqual(ctx.exception.known_modules, {SomeModule})
        return ctx.exception

    @validate_output
    def test_container_refuses_to_provide_before_registrations_are_closed(self) -> HelpfulException:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotProvideUntilRegistrationsAreClosed) as ctx:
            container.provide(SomeModule.a)

        return ctx.exception

    def test_cannot_provide_raw_type_even_if_signature_says_so(self) -> None:
        container = Container.empty()
        container.ready()

        class SomeClass:
            pass

        with self.assertRaises(CannotProvideRawType) as ctx:
            container.provide(SomeClass)
        self.assertEqual(ctx.exception.type, SomeClass)

    @validate_output
    def test_refuses_to_provide_resource_not_defined_on_the_original_provider(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        class AnotherProvider(Provider, module=SomeModule):
            b = Resource(int)

            def provide_b(self) -> int:
                return 11

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.ready(allow_provider_resources=True)

        with self.assertRaises(ProviderResourceOfUnregisteredProvider) as ctx:
            container.provide(AnotherProvider.b)
        self.assertEqual(ctx.exception.resource.provider, AnotherProvider)
        self.assertEqual(ctx.exception.provider_in_use, SomeProvider)
        return ctx.exception


class TestContainerProvidesPrivateResources(TestCaseWithOutputFixtures):
    def test_can_provide_private_resource(self) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(int)

            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready(allow_provider_resources=True)
        self.assertEqual(container.provide(SomeProvider.a), 10)

    def test_provider_method_can_depend_on_private_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)


class TestContainerProvidesOverridingResources(TestCaseWithOutputFixtures):
    def test_can_provide_overriding_resource(self) -> None:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            pass

        class SomeModule(Module):
            a = Resource(SomeBaseClass)

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(SomeConcreteClass)

            def provide_a(self) -> SomeConcreteClass:
                return SomeConcreteClass()

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready(allow_provider_resources=True)

        from_overriden = container.provide(SomeProvider.a)
        self.assertIsInstance(from_overriden, SomeConcreteClass)
        from_module = container.provide(SomeModule.a)
        self.assertIs(from_overriden, from_module)

    def test_provider_method_can_depend_on_private_resource(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container()
        container.register(SomeModule, SomeProvider)
        container.ready()
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
            some = Resource(SomeBaseClass)
            another = Resource(AnotherClass)

        class SomeProvider(Provider, module=SomeModule):
            some = Resource(SomeConcreteClass)

            def provide_some(self) -> SomeConcreteClass:
                return SomeConcreteClass()

            def provide_another(self, some: SomeConcreteClass) -> AnotherClass:
                return AnotherClass(some)

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()

        another = container.provide(SomeModule.another)
        self.assertIsInstance(another, AnotherClass)
        some = container.provide(SomeModule.some)
        self.assertIsInstance(some, SomeConcreteClass)
        self.assertIs(another.some, some)


class TestContainerCallingProviderMethods(TestCaseWithOutputFixtures):
    def test_provider_methods_can_depend_on_resources_from_another_module(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        class AnotherModule(Module):
            b = Resource(int)

        class AnotherProvider(Provider, module=AnotherModule):
            def provide_b(self, a: SomeModule.a) -> int:  # type: ignore
                return a + 1

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.register(AnotherModule, AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(AnotherModule.b), 11)

    def test_provider_methods_can_depend_on_resources_from_the_same_module(
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

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_methods_can_depend_on_resources_from_the_same_module_via_annotation(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)
            b = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: SomeModule.b) -> int:  # type: ignore
                return b + 1

            def provide_b(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_methods_can_depend_on_resources_declared_as_resource_instances(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)
            b = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: SomeModule.b) -> int:  # type: ignore
                # mypy doesn´t like implicit aliases, pyright types just fine.
                return b + 1  # pyright: ignore

            def provide_b(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    @validate_output
    def test_provider_method_cannot_access_the_provider_instance(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class ProviderAssumingInstanceIsAvailable(Provider, module=SomeModule):
            def provide_a(self) -> int:
                if getattr(self, "cache", None) is None:
                    setattr(self, "cache", 10)
                return self.cache  # type: ignore

        container = Container.empty()
        container.register(SomeModule, ProviderAssumingInstanceIsAvailable)
        container.ready()
        with self.assertRaises(ProviderMethodsCantAccessProviderInstance) as ctx:
            container.provide(SomeModule.a)

        self.assertEqual(ctx.exception.resource, SomeModule.a)
        self.assertEqual(
            ctx.exception.provider_method,
            get_provider_method(ProviderAssumingInstanceIsAvailable, SomeModule.a),
        )
        return ctx.exception


class TestContainerRegistration(TestCaseWithOutputFixtures):
    @validate_output
    def test_container_disallows_registering_a_module_twice(self) -> HelpfulException:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(ModuleAlreadyRegistered) as ctx:
            container.register(SomeModule, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})
        return ctx.exception

    @validate_output
    def test_container_register_provider_must_provide_for_module(self) -> HelpfulException:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
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
        return ctx.exception

    def test_can_register_module_and_provider_independently(self) -> None:
        class SomeModule(Module):
            a = int
            pass

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule)
        container.register_provider(SomeProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 10)

    @validate_output
    def test_cannot_register_two_providers_for_the_same_module(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        class AnotherProvider(Provider, module=SomeModule):
            pass

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.registering, AnotherProvider)
        return ctx.exception

    @validate_output
    def test_cannot_register_same_provider_twice(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(SomeProvider)

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.registering, SomeProvider)
        return ctx.exception

    @validate_output
    def test_cant_register_module_after_registrations_are_closed(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        container = Container.empty()
        container.ready()
        with self.assertRaises(RegistrationsAreClosed) as ctx:
            container.register(SomeModule)
        self.assertEqual(ctx.exception.registering, SomeModule)
        return ctx.exception

    @validate_output
    def test_cant_register_provider_after_registrations_are_closed(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            pass

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider, module=SomeModule):
            pass

        container = Container.empty()
        container.register(SomeModule)
        container.ready()
        with self.assertRaises(RegistrationsAreClosed) as ctx:
            container.register_provider(AnotherProvider)
        self.assertEqual(ctx.exception.registering, AnotherProvider)
        return ctx.exception


class TestContainerTampering(TestCaseWithOutputFixtures):
    def test_can_override_a_provider_when_tampering(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.tamper(allow_overrides=True)

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_can_override_a_default_provider_when_tampering_without_overrides_enabled(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        container = Container.empty()
        container.register(SomeModule)
        container.ready()
        container.tamper(allow_overrides=True)

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    @validate_output
    def test_cannot_reopen_for_registration_once_a_resource_has_been_provided(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.provide(SomeModule.a)
        with self.assertRaises(CannotTamperAfterHavingProvidedResources) as ctx:
            container.tamper()

        self.assertEqual(ctx.exception.container, container)
        return ctx.exception

    @validate_output
    def test_container_must_be_ready_before_tampering_with_it(self) -> HelpfulException:
        container = Container()
        with self.assertRaises(CannotTamperUntilContainerIsReady) as ctx:
            container.tamper()
        self.assertEqual(ctx.exception.container, container)
        return ctx.exception

    @validate_output
    def test_ready_container_refuses_to_be_made_ready_again(self) -> HelpfulException:
        container = Container()
        container.ready()
        with self.assertRaises(ContainerAlreadyReady) as ctx:
            container.ready()
        self.assertEqual(ctx.exception.container, container)
        return ctx.exception

    @validate_output
    def test_cannot_override_provider_on_tampered_container_if_overrides_are_not_explicitly_allowed(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.tamper()

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        with self.assertRaises(CannotOverrideRegisteredProvider) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.registered, SomeProvider)
        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.registering, AnotherProvider)
        return ctx.exception

    @validate_output
    def test_container_cannot_be_tampered_twice(self) -> HelpfulException:
        container = Container.empty()
        container.ready()

        container.tamper()
        container.ready()

        with self.assertRaises(CannotTamperWithContainerTwice) as ctx:
            container.tamper()

        self.assertEqual(ctx.exception.container, container)
        return ctx.exception

    def test_can_restore_container_after_tampering(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.tamper(allow_overrides=True)

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)
        container.restore()
        self.assertEqual(container.provide(SomeModule.a), 10)

    @validate_output
    def test_restoring_container_doesn_allow_for_more_registrations(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.tamper()
        container.restore()

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        with self.assertRaises(RegistrationsAreClosed) as ctx:
            container.register_provider(AnotherProvider)

        return ctx.exception

    def test_can_tamper_container_again_after_restoring(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        container.ready()
        container.tamper(allow_overrides=True)

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        container.register_provider(AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)
        container.restore()

        class YetAnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 12

        container.tamper(allow_overrides=True)
        container.register_provider(YetAnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 12)

        container.restore()
        self.assertEqual(container.provide(SomeModule.a), 10)

    @validate_output
    def test_container_refuses_to_restore_if_not_previously_tampered_with(self) -> HelpfulException:
        container = Container.empty()
        with self.assertRaises(ContainerWasNotTamperedWith) as ctx:
            container.restore()
        self.assertEqual(ctx.exception.container, container)
        return ctx.exception


class TestContainerImplicitProviders(TestCaseWithOutputFixtures):
    @validate_output
    def test_cant_register_implicit_provider(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class AnotherModule(Module):
            b = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: AnotherModule.b) -> int:  # type: ignore
                return b + 1

        class AnotherProvider(Provider, module=AnotherModule):
            def provide_b(self) -> int:
                return 10

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CannotRegisterProviderToNotRegisteredModule) as ctx:
            container.register_provider(AnotherProvider)

        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.registered_modules, {SomeModule})
        return ctx.exception

    def test_can_register_implicit_provider_if_reopened_explicitly_and_module_is_used(
        self,
    ) -> None:
        class Module1(Module):
            a = Resource(int)

        class Module2(Module):
            b = Resource(int)

        class Provider1(Provider, module=Module1):
            def provide_a(self, b: Module2.b) -> int:  # type: ignore
                return b + 1

        class Provider2(Provider, module=Module2):
            def provide_b(self) -> int:
                return 10

        Module2.default_provider = Provider2

        class AnotherProvider2(Provider, module=Module2):
            def provide_b(self) -> int:
                return 11

        container = Container.empty()
        container.register(Module1, Provider1)
        container.ready()
        container.tamper(allow_overrides=True, allow_implicit_modules=True)
        container.register_provider(AnotherProvider2)
        container.ready()
        self.assertEqual(container.provide(Module1.a), 12)

    @validate_output
    def test_container_fails_on_closing_registration_if_any_implicit_provider_is_unused(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        container = Container.empty()
        container.ready()
        container.tamper(allow_overrides=True, allow_implicit_modules=True)
        container.register_provider(SomeProvider)
        with self.assertRaises(RegisteredProvidersNotUsed) as ctx:
            container.ready()
        self.assertEqual(ctx.exception.providers, {SomeProvider})
        return ctx.exception


class TestDefaultProvider(TestCaseWithOutputFixtures):
    @validate_output
    def test_container_cant_seal_if_a_module_lacks_a_provider(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        container = Container.empty()
        container.register(SomeModule)
        with self.assertRaises(ModuleWithoutRegisteredOrDefaultProvider) as ctx:
            container.ready()

        self.assertEqual(ctx.exception.module, SomeModule)
        return ctx.exception

    def test_container_uses_default_provider_if_none_registered(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider
        container = Container.empty()
        container.register(SomeModule)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_container_uses_registered_provider_over_default_provider(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 11

        container = Container.empty()
        container.register(SomeModule, AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_setting_default_container_after_sealing_has_no_effect(self) -> None:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        SomeModule.default_provider = SomeProvider

        class AnotherProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                raise Exception("this provider was set after sealing!")

        container = Container.empty()
        container.register(SomeModule)
        container.ready()

        SomeModule.default_provider = AnotherProvider
        self.assertEqual(container.provide(SomeModule.a), 10)


class TestProviderSubclasses(TestCaseWithOutputFixtures):
    def test_provider_subclass_can_act_as_provider_and_use_base_methods_for_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            pass

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 10)

    def test_provider_subclass_can_act_as_provider_and_use_base_method_for_overriding_resource(
        self,
    ) -> None:
        class SomeClass:
            pass

        class ConcreteClass(SomeClass):
            pass

        class SomeModule(Module):
            some = Resource(SomeClass)

        class SomeProvider(Provider, module=SomeModule):
            some = Resource(ConcreteClass)

            def provide_some(self) -> ConcreteClass:
                return ConcreteClass()

        class AnotherProvider(SomeProvider):
            pass

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready(allow_provider_resources=True)
        self.assertIsInstance(container.provide(SomeModule.some), ConcreteClass)

    def test_provider_subclass_can_act_as_provider_and_use_base_method_for_private_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(int)

            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            pass

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready(allow_provider_resources=True)
        self.assertEqual(container.provide(AnotherProvider.a), 10)

    def test_provider_subclass_can_act_as_provider_and_override_methods_for_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            def provide_a(self) -> int:
                return 11

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready()
        self.assertEqual(container.provide(SomeModule.a), 11)

    def test_provider_subclass_can_act_as_provider_and_override_methods_for_private_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class SomeProvider(Provider, module=SomeModule):
            a = Resource(int)

            def provide_a(self) -> int:
                return 10

        class AnotherProvider(SomeProvider):
            def provide_a(self) -> int:
                return 11

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready(allow_provider_resources=True)
        self.assertEqual(container.provide(AnotherProvider.a), 11)

    def test_provider_subclass_can_act_as_provider_and_override_methods_for_overriding_resource(
        self,
    ) -> None:
        class SomeClass:
            pass

        class ConcreteClass(SomeClass):
            def __init__(self, param: int):
                self.param = param

        class SomeModule(Module):
            some = Resource(SomeClass)

        class SomeProvider(Provider, module=SomeModule):
            some = Resource(ConcreteClass)

            def provide_some(self) -> ConcreteClass:
                return ConcreteClass(10)

        class AnotherProvider(SomeProvider):
            def provide_some(self) -> ConcreteClass:
                return ConcreteClass(11)

        container = Container()
        container.register(SomeModule, AnotherProvider)
        container.ready(allow_provider_resources=True)
        self.assertEqual(container.provide(AnotherProvider.some).param, 11)


class TestCircularDependencies(TestCaseWithOutputFixtures):
    @validate_output_any_line_order
    def test_simplest_circular_dependency_breaks_on_seal(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, a: SomeModule.a) -> int:  # type: ignore
                return a + 1

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.ready()
        self._assert_contains_loop(
            ctx.exception.loops,
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

    @validate_output_any_line_order
    def test_single_provider_circular_dependency_breaks_on_seal(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)
            b = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: SomeModule.b) -> int:  # type: ignore
                return b + 1

            def provide_b(self, a: SomeModule.a) -> int:  # type: ignore
                return a + 1

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.ready()

        self._assert_contains_loop(
            ctx.exception.loops,
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
        return ctx.exception

    @validate_output_any_line_order
    def test_many_providers_circular_dependency_breaks_on_seal(self) -> HelpfulException:
        class ModuleA(Module):
            a = Resource(int)

        class ModuleB(Module):
            b = Resource(int)

        class ModuleC(Module):
            c = Resource(int)

        class ProviderA(Provider, module=ModuleA):
            def provide_a(self, param1: ModuleB.b) -> int:  # type: ignore
                return param1 + 1

        class ProviderB(Provider, module=ModuleB):
            def provide_b(self, param2: ModuleC.c) -> int:  # type: ignore
                return param2 + 1

        class ProviderC(Provider, module=ModuleC):
            def provide_c(self, param3: ModuleA.a) -> int:  # type: ignore
                return param3 + 1

        container = Container.empty()
        container.register(ModuleA, ProviderA)
        container.register(ModuleB, ProviderB)
        container.register(ModuleC, ProviderC)

        with self.assertRaises(CircularDependency) as ctx:
            container.ready()

        self._assert_contains_loop(
            ctx.exception.loops,
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
        return ctx.exception

    @validate_output_any_line_order
    def test_catches_inner_circular_dependency(self) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)
            b = Resource(int)
            c = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            def provide_a(self, b: int) -> int:
                return b

            def provide_b(self, c: int) -> int:
                return c

            def provide_c(self, b: int) -> int:
                return b

        container = Container.empty()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.ready()

        self._assert_contains_loop(
            ctx.exception.loops,
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
        return ctx.exception

    @validate_output_any_line_order
    def test_catches_circular_dependencies_involving_private_resources(self) -> HelpfulException:
        class SomeModule(Module):
            a = int

        class SomeProvider(Provider, module=SomeModule):
            b = int

            def provide_a(self, b: int) -> int:
                return b + 1

            def provide_b(self, a: int) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.ready()

        self._assert_contains_loop(
            ctx.exception.loops,
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
        return ctx.exception

    @validate_output_any_line_order
    def test_catches_circular_dependencies_involving_overriding_resources(self) -> HelpfulException:
        class SomeBaseClass:
            pass

        class SomeConcreteClass(SomeBaseClass):
            def __init__(self, param: int):
                self.param = param

        class SomeModule(Module):
            some = Resource(SomeBaseClass)
            a = Resource(int)

        class SomeProvider(Provider, module=SomeModule):
            some = Resource(SomeConcreteClass)
            private = Resource(int)

            def provide_a(self, some: SomeConcreteClass) -> int:
                return some.param

            def provide_some(self, private: int) -> SomeConcreteClass:
                return SomeConcreteClass(private)

            def provide_private(self, a: int) -> int:
                return a + 1

        container = Container()
        container.register(SomeModule, SomeProvider)
        with self.assertRaises(CircularDependency) as ctx:
            container.ready()

        self._assert_contains_loop(
            ctx.exception.loops,
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
        return ctx.exception

    def test_providers_can_have_a_circular_module_dependency_without_a_circular_resource_dependency(
        self,
    ) -> None:
        class Module1(Module):
            a = Resource(int)
            c = Resource(int)

        class Module2(Module):
            b = Resource(int)
            d = Resource(int)

        class Provider1(Provider, module=Module1):
            def provide_a(self) -> int:
                return 2

            def provide_c(self, b: Module2.b) -> int:  # type: ignore
                return b * 5

        class Provider2(Provider, module=Module2):
            def provide_b(self, a: Module1.a) -> int:  # type: ignore
                return a * 3

            def provide_d(self, c: Module1.c) -> int:  # type: ignore
                return c * 7

        container = Container.empty()
        container.register(Module1, Provider1)
        container.register(Module2, Provider2)
        container.ready()
        self.assertEqual(container.provide(Module2.d), 2 * 3 * 5 * 7)

    def _assert_contains_loop(
        self, loops: List[List[ResolutionStep]], expected: Sequence[ResolutionStep]
    ) -> None:
        # this check is not 100% accurate since we're allowing all steps in a circular
        # dependency to be in any order. It seems good enough though.
        if not any(set(expected) == set(loop) for loop in loops):
            self.fail("expected loop not found")


T = TypeVar("T")


def get_provider_method(provider: ProviderType, resource: Type[T]) -> ProviderMethod[T]:
    return provider[cast(ModuleResource[T], resource)]
