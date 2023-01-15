from unittest import TestCase

from wiring.resource import Resource
from wiring.provider import Provider
from wiring.module import Module
from wiring.module.errors import (
    CannotUseBaseProviderAsDefaultProvider,
    DefaultProviderProvidesToAnotherModule,
    DefaultProviderIsNotAProvider,
)


class TestModule(TestCase):
    def test_module_collects_and_bind_resources(self) -> None:
        class SomeModule(Module):
            a = Resource(int)

        resources = list(SomeModule._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)


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
