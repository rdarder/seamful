from unittest import TestCase

from .module import Module
from wiring.resource import ResourceIsNotBound, Resource, CannotRebindModule


class TestResource(TestCase):
    def test_access_unbound_resource(self):
        a = Resource(int)
        with self.assertRaises(ResourceIsNotBound) as ctx:
            a.name

        self.assertEqual(ctx.exception.resource, a)

    def test_cannot_rebind_resource(self):
        class SomeModule(Module):
            a = Resource(int)

        with self.assertRaises(CannotRebindModule) as ctx:

            class AnotherModule(Module):
                b = SomeModule.a

        self.assertEqual(ctx.exception.resource, SomeModule.a)
        self.assertEqual(ctx.exception.rebind_name, "b")
        self.assertEqual(ctx.exception.rebind_module.__name__, "AnotherModule")
