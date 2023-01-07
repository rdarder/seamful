from unittest import TestCase

from .module import Module
from .resource import Resource


class TestModule(TestCase):
    def test_module_collects_and_bind_resources(self):
        class SomeModule(Module):
            a = Resource(int)

        resources = list(SomeModule._list_resources())
        self.assertEqual(len(resources), 1)
        resource = resources[0]
        self.assertEqual(resource.name, "a")
        self.assertEqual(resource.type, int)
        self.assertEqual(resource.module, SomeModule)
