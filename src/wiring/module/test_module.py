from typing import TypeAlias
from unittest import TestCase

from wiring.provider import Provider
from wiring.module import Module
from wiring.module.errors import (
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    DefaultProviderIsNotAProvider,
    InvalidResourceAnnotation,
    InvalidAttributeAnnotation,
    CannotUseExistingResource,
    ModulesCannotBeInstantiated,
)
from wiring.resource import Resource


class TestModule(TestCase):
    def test_module_collects_resources_from_implicit_type_aliases(self) -> None:
        class SomeModule(Module):
            a = int

        resources = list(SomeModule._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)

    def test_module_collects_resources_from_explicit_type_aliases(self) -> None:
        class SomeModule(Module):
            a: TypeAlias = int

        resources = list(SomeModule._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)

    def test_module_collect_resource_instances_and_binds_them(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        resources = list(SomeModule._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)

    def test_module_fails_on_class_attribute_with_only_type_annotation(self) -> None:
        with self.assertRaises(InvalidAttributeAnnotation) as ctx:

            class SomeModule(Module):
                a: int

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.annotation, int)

    def test_module_fails_on_class_attribute_annotated_with_resource_instance(
        self,
    ) -> None:
        with self.assertRaises(InvalidResourceAnnotation) as ctx:

            class SomeModule(Module):
                a: Resource(int)  # type: ignore

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.is_bound, False)

    def test_module_fails_on_a_resource_annotated_with_an_external_module_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(InvalidResourceAnnotation) as ctx:

            class AnotherModule(Module):
                b: SomeModule.a  # type: ignore

        self.assertEqual(ctx.exception.module.__name__, "AnotherModule")
        self.assertEqual(ctx.exception.name, "b")
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.is_bound, True)
        self.assertEqual(ctx.exception.resource.module, SomeModule)
        self.assertEqual(ctx.exception.resource.name, "a")

    def test_module_fails_on_a_resource_defined_as_another_modules_resource(
        self,
    ) -> None:
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(CannotUseExistingResource) as ctx:

            class AnotherModule(Module):
                b = SomeModule.a

        self.assertEqual(ctx.exception.module.__name__, "AnotherModule")
        self.assertEqual(ctx.exception.name, "b")
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.is_bound, True)
        self.assertEqual(ctx.exception.resource.module, SomeModule)
        self.assertEqual(ctx.exception.resource.name, "a")


class TestModuleInstances(TestCase):
    def test_modules_cannot_be_instantiated(self) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(ModulesCannotBeInstantiated) as ctx:
            SomeModule()
        self.assertEqual(ctx.exception.module, SomeModule)

    def test_modules_cannot_be_instantiated_even_if_defining_constructor(self) -> None:
        class SomeModule(Module):
            def __init__(self) -> None:
                pass

        with self.assertRaises(ModulesCannotBeInstantiated) as ctx:
            SomeModule()
        self.assertEqual(ctx.exception.module, SomeModule)


class TestModuleDefaultProvider(TestCase):
    def test_cant_use_base_provider_as_default_provider(self) -> None:
        class SomeModule(Module):
            pass

        with self.assertRaises(CannotUseBaseProviderAsDefaultProvider) as ctx:
            SomeModule.default_provider = Provider

        self.assertEqual(ctx.exception.module, SomeModule)

    def test_cant_set_a_default_provider_to_one_that_provides_to_another_module(
        self,
    ) -> None:
        class SomeModule(Module):
            pass

        class AnotherModule(Module):
            pass

        class AnotherProvider(Provider[AnotherModule]):
            pass

        with self.assertRaises(DefaultProviderProvidesToAnotherModule) as ctx:
            SomeModule.default_provider = AnotherProvider

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.provider.module, AnotherModule)

    def test_cant_set_a_default_provider_to_something_not_a_provider(self) -> None:
        class SomeModule(Module):
            pass

        class NotAProvider:
            pass

        with self.assertRaises(DefaultProviderIsNotAProvider) as ctx:
            SomeModule.default_provider = NotAProvider  # type: ignore

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.not_provider, NotAProvider)
