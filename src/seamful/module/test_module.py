import sys
from unittest import TestCase, skipIf

from seamful.provider import Provider
from seamful.module import Module
from seamful.module.errors import (
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    DefaultProviderIsNotAProvider,
    CannotUseExistingModuleResource,
    ModulesCannotBeInstantiated,
    InvalidPrivateResourceInModule,
    InvalidOverridingResourceInModule,
    ModulesMustInheritDirectlyFromModuleClass,
    InvalidModuleAttributeType,
    InvalidPrivateModuleAttribute,
    InvalidModuleAttributeName,
)
from seamful.errors import HelpfulException
from seamful.resource import Resource, ModuleResource, ResourceKind
from seamful.utils_for_tests import validate_output, TestCaseWithOutputFixtures


class TestModuleResourcesFromTypeAlias(TestCase):
    def test_module_collects_resources_from_implicit_type_aliases(self) -> None:
        class SomeModule(Module):
            a = int

        resources = list(SomeModule)
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)

    @skipIf(sys.version_info < (3, 10), "Type aliases are not supported")
    def test_module_collects_resources_from_explicit_type_aliases(self) -> None:
        from typing import TypeAlias

        class SomeModule(Module):
            a: TypeAlias = int

        resources = list(SomeModule)
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)


class TestModuleResourcesFromResourceInstances(TestCaseWithOutputFixtures):
    def test_module_collect_resource_instances_and_binds_them(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        resources = list(SomeModule)
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertIs(resource, SomeModule.a)
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)

    @validate_output
    def test_module_fails_on_a_resource_defined_as_another_modules_resource(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(CannotUseExistingModuleResource) as ctx:

            class AnotherModule(Module):
                b = SomeModule.a

        self.assertEqual(ctx.exception.module.__name__, "AnotherModule")
        self.assertEqual(ctx.exception.name, "b")
        self.assertIsInstance(ctx.exception.resource, ModuleResource)
        self.assertEqual(ctx.exception.resource.type, int)
        self.assertEqual(ctx.exception.resource.module, SomeModule)
        self.assertEqual(ctx.exception.resource.name, "a")
        return ctx.exception

    @validate_output
    def test_module_refuses_definition_of_private_resource_in_it(
        self,
    ) -> HelpfulException:
        with self.assertRaises(InvalidPrivateResourceInModule) as ctx:

            class SomeModule(Module):
                a = Resource(int, ResourceKind.PRIVATE)

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.type, int)
        return ctx.exception

    @validate_output
    def test_module_refuses_definition_of_overriding_resource_in_it(
        self,
    ) -> HelpfulException:
        with self.assertRaises(InvalidOverridingResourceInModule) as ctx:

            class SomeModule(Module):
                a = Resource(int, ResourceKind.OVERRIDE)

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.type, int)
        return ctx.exception


class TestModuleClassDeclaration(TestCaseWithOutputFixtures):
    @validate_output
    def test_modules_cannot_be_instantiated(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        with self.assertRaises(ModulesCannotBeInstantiated) as ctx:
            SomeModule()
        self.assertEqual(ctx.exception.module, SomeModule)
        return ctx.exception

    @validate_output
    def test_modules_cannot_be_instantiated_even_if_defining_constructor(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            def __init__(self) -> None:
                pass

        with self.assertRaises(ModulesCannotBeInstantiated) as ctx:
            SomeModule()
        self.assertEqual(ctx.exception.module, SomeModule)
        return ctx.exception

    @validate_output
    def test_modules_cannot_be_defined_as_a_subclass_of_another_module(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            pass

        with self.assertRaises(ModulesMustInheritDirectlyFromModuleClass) as ctx:

            class SubModule(SomeModule):
                pass

        self.assertEqual(ctx.exception.module_class_name, "SubModule")
        self.assertEqual(ctx.exception.inherits_from, (SomeModule,))
        return ctx.exception

    @validate_output
    def test_module_classes_cannot_have_private_attributes(self) -> HelpfulException:
        with self.assertRaises(InvalidPrivateModuleAttribute) as ctx:

            class SomeModule(Module):
                _something = int

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "_something")
        self.assertEqual(ctx.exception.attribute_value, int)
        return ctx.exception

    @validate_output
    def test_module_classes_cannot_have_an_attribute_named_default_provider(
        self,
    ) -> HelpfulException:
        with self.assertRaises(InvalidModuleAttributeName) as ctx:

            class SomeModule(Module):
                default_provider = int

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "default_provider")
        self.assertEqual(ctx.exception.attribute_value, int)
        return ctx.exception

    @validate_output
    def test_module_classes_attributes_must_be_types_or_resources(
        self,
    ) -> HelpfulException:
        with self.assertRaises(InvalidModuleAttributeType) as ctx:

            class SomeModule(Module):
                a = 10

        self.assertEqual(ctx.exception.module.__name__, "SomeModule")
        self.assertEqual(ctx.exception.name, "a")
        self.assertEqual(ctx.exception.attribute_value, 10)
        return ctx.exception


class TestModuleDefaultProvider(TestCaseWithOutputFixtures):
    @validate_output
    def test_cant_use_base_provider_as_default_provider(self) -> HelpfulException:
        class SomeModule(Module):
            pass

        with self.assertRaises(CannotUseBaseProviderAsDefaultProvider) as ctx:
            SomeModule.default_provider = Provider

        self.assertEqual(ctx.exception.module, SomeModule)
        return ctx.exception

    @validate_output
    def test_cant_set_a_default_provider_to_one_that_provides_to_another_module(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            pass

        class AnotherModule(Module):
            pass

        class AnotherProvider(Provider, module=AnotherModule):
            pass

        with self.assertRaises(DefaultProviderProvidesToAnotherModule) as ctx:
            SomeModule.default_provider = AnotherProvider

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.provider, AnotherProvider)
        self.assertEqual(ctx.exception.provider.module, AnotherModule)
        return ctx.exception

    @validate_output
    def test_cant_set_a_default_provider_to_something_not_a_provider(
        self,
    ) -> HelpfulException:
        class SomeModule(Module):
            pass

        class NotAProvider:
            pass

        with self.assertRaises(DefaultProviderIsNotAProvider) as ctx:
            SomeModule.default_provider = NotAProvider  # type: ignore

        self.assertEqual(ctx.exception.module, SomeModule)
        self.assertEqual(ctx.exception.not_provider, NotAProvider)
        return ctx.exception
