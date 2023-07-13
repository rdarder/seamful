from __future__ import annotations
from dataclasses import dataclass
from itertools import chain
from typing import Union, Any, Type, cast, TYPE_CHECKING

from seamful.errors import HelpfulException, Text, qname, sname, rdef, point_to_definition, rname
from seamful.module.module_type import ModuleType
from seamful.resource import ModuleResource, ProviderResource, BoundResource
from seamful.provider.provider_type import ProviderType, ProviderMethod

if TYPE_CHECKING:
    from seamful.application import Application


class ModuleNotRegisteredForResource(HelpfulException):
    def __init__(
        self,
        resource: BoundResource[Any],
        registered_modules: set[ModuleType],
        known_modules: set[ModuleType],
    ):
        self.resource = resource
        self.registered_modules = registered_modules
        self.known_modules = known_modules

    def explanation(self) -> str:
        t = Text("Attempted to provide for resource:")
        t.indented_line(rdef(self.resource))
        t.newline("Which doesn't belong to any registered module. Registered modules are:")
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to provide for resource that does not belong to any registered module."


class ModuleAlreadyRegistered(HelpfulException):
    def __init__(self, module: ModuleType, registered_modules: set[ModuleType]):
        self.module = module
        self.registered_modules = registered_modules

    def explanation(self) -> str:
        t = Text(f"Attempted to install module {qname(self.module)}")
        t.sentence("which is already registered. Registered modules are:")
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to install module that is already registered."


class ProviderModuleMismatch(HelpfulException):
    def __init__(self, provider: ProviderType, module: ModuleType):
        self.provider = provider
        self.module = module

    def explanation(self) -> str:
        t = Text(
            f"Attempted to install_module({sname(self.module)}, provider={sname(self.provider)}) "
            f"but {qname(self.provider)} provides for module {qname(self.provider.module)} "
            f"instead."
        )
        t.blank()
        t.newline(point_to_definition(self.provider))
        t.newline(point_to_definition(self.module))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to install a provider alongside a module, "
            "but the provider provides for a different module."
        )


class CannotRegisterProviderToNotRegisteredModule(HelpfulException):
    def __init__(self, provider: ProviderType, registered_modules: set[ModuleType]):
        self.provider = provider
        self.registered_modules = registered_modules

    def explanation(self) -> str:
        t = Text(f"Attempted to install provider {qname(self.provider)}")
        t.sentence(
            f"which provides for {qname(self.provider.module)}, "
            f"which is not registered. Registered modules are:"
        )
        with t.indented_block(blank_before=False):
            for module in self.registered_modules:
                t.newline(f"- {sname(module)}")
        t.newline(
            "Registering providers for implicit modules is only meant to be used for "
            "testing and secondary scenarios, and can be enabled by tampering with the application:"
        )
        t.indented_line("application.tamper(allow_implicit_modules=True)")
        t.blank()
        t.newline(
            "If instead, the application is expected to provide resources for "
            f"{qname(self.provider.module)}, you can register both at once by calling:"
        )
        t.indented_line(
            f"application.register({sname(self.provider.module)}, provider={sname(self.provider)})"
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to install a provider for a module that is not registered."


class CannotOverrideRegisteredProvider(HelpfulException):
    def __init__(self, module: ModuleType, *, registered: ProviderType, registering: ProviderType):
        self.module = module
        self.registered = registered
        self.registering = registering

    def explanation(self) -> str:
        t = Text(f"Attempted to install provider {qname(self.registering)}")
        if self.registered is self.registering:
            t.sentence("which is already registered.")
        else:
            t.sentence(
                f"which provides for {qname(self.module)}, "
                f"but {qname(self.registered)} was already registered as its provider."
            )

            t.blank()

            t.newline(
                "Overriding providers is not allowed. You can enable overriding a provider "
                "after the application is ready tampering with it:"
            )
            t.indented_line("application.tamper(allow_overrides=True)")
            t.blank()
            t.newline(
                "Keep in mind that overriding providers is mostly meant for testing "
                "and alternative running scenarios."
            )
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to install a provider for a module that already "
            "has a registered provider."
        )


class ModuleWithoutRegisteredOrDefaultProvider(HelpfulException):
    def __init__(self, module: ModuleType):
        self.module = module

    def explanation(self) -> str:
        t = Text(f"Module {qname(self.module)} has no registered or default provider.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "A registered module has no registered or default provider."


class CannotProvideUntilApplicationIsReady(HelpfulException):
    def explanation(self) -> str:
        t = Text(
            "Attempted to provide a resource before application is ready for providing. "
            "You can make the application ready by calling:"
        )
        t.indented_line("application.ready()")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to provide a resource before registrations were closed."


class CantInstallWhenReadyToProvide(HelpfulException):
    def __init__(self, registering: Union[ModuleType, ProviderType]):
        self.registering = registering

    def explanation(self) -> str:
        from seamful.module.module_type import ModuleType
        from seamful.provider.provider_type import ProviderType

        if isinstance(self.registering, ModuleType):
            t = Text(f"Attempted to install module {qname(self.registering)}")
        elif isinstance(self.registering, ProviderType):
            t = Text(f"Attempted to install provider {qname(self.registering)}")
        else:
            raise TypeError()
        t.sentence(", but registrations are closed since the application is ready for providing.")
        t.blank()
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to install a module or provider after being ready for providing."


class CannotProvideRawType(Exception):
    def __init__(self, t: type):
        self.type = t


@dataclass(frozen=True)
class ResolutionStep:
    target: BoundResource[Any]
    provider_method: ProviderMethod[Any]
    parameter_name: str
    depends_on: BoundResource[Any]

    @classmethod
    def from_types(
        cls,
        target: Type[Any],
        provider_method: ProviderMethod[Any],
        parameter_name: str,
        depends_on: Type[Any],
    ) -> ResolutionStep:
        return ResolutionStep(
            target=cast(BoundResource[Any], target),
            provider_method=provider_method,
            parameter_name=parameter_name,
            depends_on=cast(ModuleResource[Any], depends_on),
        )

    def __str__(self) -> str:
        m = self.provider_method
        return (
            f"{rname(self.target)} -> "
            f"{m.provider.__name__}.provide_{self.target.name}"
            f"(..., {self.parameter_name}: {rname(self.depends_on)})"
        )


class CircularDependency(HelpfulException):
    def __init__(self, loops: list[list[ResolutionStep]]):
        self.loops = loops

    def explanation(self) -> str:
        t = Text(wrap=False)
        if len(self.loops) == 1:
            t.newline("Circular dependency detected:")
            self.add_loop(t, self.loops[0])
        else:
            t.newline(f"Circular dependencies detected ({len(self.loops)}):")
            for i, loop in enumerate(self.loops):
                t.newline(f"{i + 1}:")
                self.add_loop(t, loop)

        providers = {step.provider_method.provider for step in chain(*self.loops)}
        t.blank()
        t.newline("Providers involved:")
        with t.indented_block(blank_before=False):
            for provider in providers:
                t.newline(f"- {point_to_definition(provider)}")
        return str(t)

    def add_loop(self, t: Text, loop: list[ResolutionStep]) -> None:
        with t.indented_block(blank_before=False):
            for step in loop:
                t.newline(str(step))

    def failsafe_explanation(self) -> str:
        return "Circular dependency detected."


class InvalidProviderInstanceAccess(Exception):
    # internal, see ProviderMethodsCantAccessProviderInstance
    pass


class ProviderMethodsCantAccessProviderInstance(HelpfulException):
    def __init__(
        self,
        resource: BoundResource[Any],
        provider_method: ProviderMethod[Any],
    ):
        self.resource = resource
        self.provider_method = provider_method

    def explanation(self) -> str:
        t = Text("Provider method:")
        with t.indented_block():
            t.newline(f"{sname(self.provider_method.provider)}.provide_{self.resource.name}()")
        t.newline("Attempted to access the provider instance 'self'.")
        t.sentence(
            "Provider methods can only access their parameters, " "but not the provider instance"
        )
        t.blank()
        t.newline(point_to_definition(self.provider_method.provider))
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Provider method attempted to access the provider instance 'self', "
            "which is not allowed."
        )


class CannotTamperUntilApplicationIsReady(HelpfulException):
    def __init__(self, application: Application) -> None:
        self.application = application

    def explanation(self) -> str:
        t = Text("Attempted to tamper with a application, but it's not ready yet.")
        t.newline(
            "Registrations on a application are open until the application is ready for providing."
        )
        t.sentence(
            "Only once the application is ready for providing, registrations will be closed,"
        )
        t.sentence("and then they can only be enabled again by calling application.tamper().")
        t.newline(
            "Keep in mind that reopening a application is meant "
            "for testing or alternative scenarios"
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to tamper with a application, but the application "
            "isn't ready for providing yet."
        )


class ApplicationAlreadyReady(HelpfulException):
    def __init__(self, application: Application):
        self.application = application

    def explanation(self) -> str:
        return "Attempted to make a application ready for providing, but it's already ready."

    def failsafe_explanation(self) -> str:
        return "Attempted to make a application ready for providing, but it's already ready."


class CannotTamperAfterHavingProvidedResources(HelpfulException):
    def __init__(self, application: Application):
        self.application = application

    def explanation(self) -> str:
        t = Text(
            "Attempted to tamper with a application, " "but it has already provided resources."
        )
        t.newline("A application can only be tampered with before it has provided any resources.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted tamper with a application, but it has already provided resources."


class RegisteredProvidersNotUsed(HelpfulException):
    def __init__(self, providers: set[ProviderType]):
        self.providers = providers

    def explanation(self) -> str:
        t = Text("The following providers were registered, but not used:")
        with t.indented_block():
            for provider in self.providers:
                t.newline(f"- {point_to_definition(provider)}")

        t.newline(
            "Those providers were explicitly registered, "
            "but the modules they provide for were not, "
            "and those modules are also not part "
            "of the dependency graph of any other used provider"
        )
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Some registered providers were not used."


class ProviderResourceOfUnregisteredProvider(HelpfulException):
    def __init__(self, resource: ProviderResource[Any], provider_in_use: ProviderType):
        self.resource = resource
        self.provider_in_use = provider_in_use

    def explanation(self) -> str:
        provider = self.resource.provider
        t = Text(
            f"Requested to provide {rname(self.resource)}, "
            f"but {qname(provider)} was not registered."
        )

        t.blank()
        t.newline(f"{qname(provider)} provides for {qname(provider.module)},")
        t.sentence(f"but that module is being provided by {qname(self.provider_in_use)}.")
        t.blank()
        t.newline(point_to_definition(provider))
        t.newline(point_to_definition(provider.module))
        t.newline(point_to_definition(self.provider_in_use))
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Requested to provide a resource of an unregistered provider."


class CannotTamperWithApplicationTwice(HelpfulException):
    def __init__(self, application: Application):
        self.application = application

    def explanation(self) -> str:
        t = Text("Attempted to tamper with a application twice.")
        t.newline("A application can be tampered once and used to provide resources,")
        t.sentence("but it needs to be restore()'d before it can be tampered with again.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return "Attempted to tamper with a application twice before restoring it."


class ApplicationWasNotTamperedWith(HelpfulException):
    def __init__(self, application: Application):
        self.application = application

    def explanation(self) -> str:
        t = Text("Attempted to restore a application that was not tampered with,")
        t.sentence("or one that was already restored")
        t.newline("A application can only be restored if it was tampered with before.")
        return str(t)

    def failsafe_explanation(self) -> str:
        return (
            "Attempted to restore a application that was not tampered with, "
            "or one that was already restored"
        )
