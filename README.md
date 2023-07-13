Seamful is a dependency injection library for Python.

It aims to facilitate writing integration tests that replace the minimum amount of dependencies with test doubles. It incentivizes using _working_ test doubles as opposed inspectable mocks.

Seamful intervenes by instantiating the objects and their dependencies. While typically one would manually instantiate these:

```python
my_service = MyService(MyRepository(...))
my_service.do_something()
```

If instantiation happens "close" to the actual working code, it is hard to replace the dependencies with test_doubles.

Seamful introduces a way of declaring which are these classes that are meant to be instantiated, and recipes for how to
build them. Moreover it provides a way of configuring those recipes so that, for example, a test environment can depart
from the production configuration just for a few of those classes.

For declaring which classes are meant to be instantiated, Seamful uses a concept called "Module". A module is a class
which contains a list of resources, which are the classes that are meant to be instantiated. For example:

```python
from seamful import Module, Resource


class PaymentsModule(Module):
    service = Resource(PaymentsService)
    repository = Resource(PaymentsRepository)
```

This states that the PaymentsModule has two resources: service and repository. It also states that they ought to be instances of PaymentsService and PaymentsRepository respectively, but it doesn't say how to build them. Since we want to be able to build them in more than one way, we want to put those recipes in a different declaration, which we call a Provider.

A provider is a class that's bound to a specific Module and specifiies builder methods for all the resources in that Module. For example:

```python
class PaymentsProvider(Provider, module=PaymentsModule):

    def get_repository(self) -> PaymentsRepository:
        return PaymentsRepository(...)

    def get_service(self, repository: PaymentsModule.repository) -> PaymentsService:
        return PaymentsService(repository)
```


While the first method seems straightforward, the second is more surprising. Instead of get_service calling self.get_repository(), it just "asks" for the resource it wants as a function parameter. This are pretty much the main rules for defining a provider method:

- must be called get_<name_of_the_resource>
- doesn't use the self parameter
- if it needs an instance of another resource, from it's module or another module, it requests it as a parameter.
- annotates its parameter types and return type.
- returns an instance of the resource it is meant to build.

Also, declaring a provider also need to follow a few rules:

- it must inherit from Provider
- it must state which module it provides for via the module= parameter
- it must have a method for each resource in the module, with the name get_<name_of_the_resource>

Once you have at least one Module and one Provider, you can wire them together in a Application. A application is the entry point for both registering modules and providers and for finally requesting module resources.

They're built as follows:

```python
from seamful import Application

application = Application.empty()
application.install_module(PaymentsModule, PaymentsProvider)
application.ready()
```

Once a application registered some modules and providers, it can become ready for providing resources. `application.ready()` checks that the module resources can be built by following the dependency graphs of the providers, which usually become more complex than the example above.

The application can be built and registered as a pubilc, global variable in your application. Then, in the entry points of your application you can import that application and ask for any of the registered modules resources. For example:

```python

from .application import application

class Main:
    def __init__(self):
        self.service = application.provide(PaymentsModule.service)

    def run(self):
        service.do_something()


```

You can actually use the application anywhere in your application, but it's recommended to use it only in the entry points. Every class that explicitly uses a application will be harder to use in a different use case.

This application can run as-is in production, but it can also be used in integration tests, where the application can be configured to provide a different implementation of some of those resources. Let's imagine that the `PaymentsRepository` uses a database that we wish not to use in our integration tests. We can create a test_double:

```python
class InMemoryPaymentsRepository(PaymentsRepository):
    def __init__(self):
        self.payments = []

    def save_payment(self, payment: Payment) -> int:
        self.payments.append(payment)
        return len(self.payments) - 1

    def get_payment(self, id: int) -> Payment:
        return self.payments[id]

    def list_payments(self) -> Iterable[Payment]:
        return self._payments[:]
```

And then we can configure the application to provide that implementation instead of the real one:

```python


import unittest
from .application import application


class PaymentProviderForTests(PaymentsProvider):
    def get_repository(self) -> PaymentsRepository:
        return InMemoryPaymentsRepository()


class TestPayments(unittest.TestCase):
    def setUp(self):
        application.tamper()
        application.install_provider(PaymentProviderForTests)
        application.ready()

    def tearDown():
        application.restore()

    def test_payment_processes_successfully(self):
        service = application.provide(PaymentsModule.service)
        service.process_new_payment(...)
        self.assertEqual(1, len(service.repository.list_payments()))
```

So far this seems like a lot of boilerplate for something that could be done with a few lines of code and Mocks. The expectation is that as your application grows bigger, the impact of this boilerplate will be less than manually instantiating the object graph manually.

Also, the ability to override only those dependencies that ought to be different in tests ensures that the code being tested is as close as possible as the real application.

Finally, even the outermost part of the application could be tested in this setup. For example:

```python
class TestPayments(unittest.TestCase):
    ...

    def test_command_line_application():
        main = Main()
        repository = application.provide(PaymentsModule.repository)
        main.run(...)
        self.assertEqual(repository.get_payment(0), Payment(...))
```

This example is rather basic but it should help get you started.
