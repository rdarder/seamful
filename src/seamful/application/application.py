from __future__ import annotations
from typing import TypeVar, Optional, Type, cast

from seamful.application.registry import Registry
from seamful.application.graph_provider import ModuleGraphProvider
from seamful.resource import BoundResource
from seamful.module.module_type import ModuleType
from seamful.provider.provider_type import ProviderType
from seamful.application.errors import (
    ProviderModuleMismatch,
    CantInstallWhenReadyToProvide,
    CannotProvideRawType,
    CannotProvideUntilApplicationIsReady,
    CannotTamperUntilApplicationIsReady,
    ApplicationAlreadyReady,
    CannotTamperAfterHavingProvidedResources,
    CannotTamperWithApplicationTwice,
    ApplicationWasNotTamperedWith,
)

T = TypeVar("T")


class Application:
    """An Application is a group of modules. Its purpose is to provide those modules resources.

    An application starts empty, without any modules or providers. It allows installing
    modules and providers for later use. Once the intended modules and providers are installed,
    the application becomes ready for provisioning them via ready().
    From there on, an Application instance will be able to provide resources of all the installed
    modules via `provide()`
    Although install/ready/provide is the main workflow of an Application, the value of this
    class (and seamful itself) is the ability to change specific resources with alternative versions
    when testing or running the program in an alternative environment. This is done via `tamper()`
    which is meant to be used solely on these alternative setups (typically in `TestCase.setUp()`)

    The methods of an Application have rather strict rules on when they can be called. This is
    because an Appplicatio is really two different things bundled together:

     - A registry for modules and providers.
     - A factory for those module resources.

    The reason they're bundled under the same class is subtle. With a few cases, it should become
    clearer why this is.
    """

    def __init__(self) -> None:
        self._is_registering = True
        self._is_providing = False

        self._checkpoint: Optional[tuple[Registry, ModuleGraphProvider]] = None
        self._registry: Registry = Registry.empty()
        self._provider: Optional[ModuleGraphProvider] = None

        self._allow_overrides = False
        self._allow_implicit_modules = False

    def install_module(self, module: ModuleType, provider: Optional[ProviderType] = None) -> None:
        """Register a module into the application, and optionally state which is the provider for
        the module.

        Registering a module on an application enables providing the module resources once the
        application is `ready()`.

        For the module to be able to provide resources, the application needs to know which is its
        provider.

        The application determines a module's provider through the following rules:

        1. If `install_module()` was called with a module _and_ a provider, it uses that one.
        2. If instead the provider was set through `install_provider()`, it uses that one.
        3. If the provider was not explicitly registered, but it has a default provider
        (Module.default_provider), it uses that one.

        A module can only be registered once. There's no need to install a module that will not be
        explicitly provided by `provide()`.

        The api is rather strict in that it disallows registering modules or providers multiple
        times.
        The intent is to make it very hard to make complex setups.
        There should be one simple set of modules registered for an application, and a subset of
        those modules having special providers for running in non production scenarios, such as
        testing or local development.

        """
        if not self._is_registering:
            raise CantInstallWhenReadyToProvide(module)
        self._registry.register_module(module)
        if provider is not None:
            if provider.module is not module:
                raise ProviderModuleMismatch(provider, module)
            self._registry.register_provider(
                provider,
                allow_override=self._allow_overrides,
                allow_implicit_module=False,
            )

    def install_provider(self, provider: ProviderType) -> None:
        """Instruct the application to use the given provider.

        In most cases, modules are registered alongside their providers via
        `install_module(module, provider)`

        The two main scenarios where `install_provider()` is useful are:

        - A module was registered through `install_module()` without setting its provider, and it
        doesn't have a default provider (or it's not appropriate for the given application).

        - A module has a provider already registered, but during tests or other alternative
        scenarios, the application is `tamper()`ed to override some of those providers.

        See `tamper()` for a more subtle third use case.

        """
        if not self._is_registering:
            raise CantInstallWhenReadyToProvide(provider)
        self._registry.register_provider(
            provider,
            allow_override=self._allow_overrides,
            allow_implicit_module=self._allow_implicit_modules,
        )

    def ready(self, allow_provider_resources: bool = False) -> None:
        """Make the application ready to provide resources for the registered modules.

        Calling `ready()` transitions the application from being registering modules to
        being available to provide resources.

        For an application to be ready, all the modules in use must have a provider, either
        their default providers or those manually set. Any used module without a provider will
        make `ready()` to fail with a descriptive message. This happens even if later no resource
        of that module is requested. The intent is to fail fast at "setup time" rather than at
        run time.

        Calling `ready()` twice raises an error. Also, an application doesn't have query methods
        such as is_ready(). This is on purpose, discouraging writing abstract or complex setups.

        Calling `provide()` before an application is `ready()` raises an error as well. Likewise,
        calling `install_module()`/`install_provider()` after the application is ready also raises
        an error.

        See tamper for special use cases meant for testing and non default environments.
        """
        if not self._is_registering:
            raise ApplicationAlreadyReady(self)
        self._provider = self._registry.solve_graph(allow_provider_resources)
        self._is_registering = False

    def provide(self, resource: Type[T]) -> T:
        """
        Provide a Module resource.

        Given a setup like this:

        ```python
        class SomeModule(Module):
            a = Resource(SomeClass)
            ...

        ...

        application.install_module(SomeModule, SomeProvider)
        application.ready()
        ```

        `application.provide(SomeModule.a)` will return an instance of `SomeClass`, built by
        `SomeProvider`.

        An application builds resources at most once, meaning that two separate calls to
        `provide()` for the same resource will yield the same object.

        The resource's Module must have been registered explicitly via `install_module()`.
        Otherwise, it'll raise an error.
        """
        if self._is_registering:
            raise CannotProvideUntilApplicationIsReady()
        if not self._is_providing:
            self._is_providing = True
            self._registry = None  # type: ignore
        if isinstance(resource, BoundResource):
            as_resource = cast(BoundResource[T], resource)
            return self._provider.provide(as_resource)  # pyright: ignore
        elif isinstance(resource, type):
            raise CannotProvideRawType(resource)
        else:
            raise NotImplementedError()

    def tamper(
        self,
        *,
        allow_overrides: bool = False,
        allow_implicit_modules: bool = False,
    ) -> None:
        """Tamper with a ready application. Useful for changing providers when testing.

        An application is typically set up in two phases:
        - Register modules and providers
        - Provide module resources.

        The phase change happens when calling `ready()`.

        When testing (or using the application in an alternative scenario such as local
        development), `tamper()`'ing with a ready application allows some providers to be changed
        with alternative ones.
        In essence, `tamper()` puts an application back into installing mode with slight changes
        in its behavior:

        - An explicitly set provider can be overriden by using install_provider() when
        allow_overrides=True. (Default providers can always be overriden when tampering.)
        - A provider can be set for a non explicitly registered module when
        allow_implicit_modules=True

        After tampering with an application, calling `ready()` again is needed for it to be
        ready for providing resources.

        Note that an application cannot be tampered many times in sequence. Once tampered (and
        possibly having used module reources), an application can go back to it's original state
        via restore().
        """
        if self._is_providing:
            raise CannotTamperAfterHavingProvidedResources(self)
        if self._is_registering:
            raise CannotTamperUntilApplicationIsReady(self)
        if self._checkpoint is not None:
            raise CannotTamperWithApplicationTwice(self)
        self._checkpoint = (self._registry, cast(ModuleGraphProvider, self._provider))
        self._registry = self._registry.copy()
        self._provider = None
        self._is_registering = True
        self._allow_overrides = allow_overrides
        self._allow_implicit_modules = allow_implicit_modules

    def restore(self) -> None:
        """Restores the state of an application that was tampered with to it's previous state.

        This effectively undoes all the module and provider registrations and overrides that
        happened after calling tamper().

        Once restored, the application is ready to provide resources.
        """
        if self._checkpoint is None:
            raise ApplicationWasNotTamperedWith(self)
        self._registry, self._provider = self._checkpoint
        self._checkpoint = None
        self._is_registering = False
        self._is_providing = False

    @classmethod
    def empty(cls) -> Application:
        """Build an empty application without any modules or providers."""
        return Application()
