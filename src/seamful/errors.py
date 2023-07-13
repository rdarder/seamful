import inspect
import os
import sys
from abc import ABC, abstractmethod
from contextlib import contextmanager
from pathlib import Path
from textwrap import wrap
from typing import Optional, Any, Iterator, TYPE_CHECKING

if TYPE_CHECKING:
    from seamful.resource import BoundResource


class Text:
    def __init__(self, title: Optional[str] = None, wrap: bool = True) -> None:
        self._lines: list[str] = []
        self._current_paragraph: list[str] = []
        self._add_blank = False
        self._wrap = wrap
        self._indent = 0
        if title is not None:
            self.newline(title)

    def sentence(self, content: str) -> None:
        self._current_paragraph.append(content)

    def newline(self, content: Optional[str] = None) -> None:
        self._flush_paragraph()
        if content is None:
            self._add_blank = True
        else:
            self.sentence(content)

    def blank(self) -> None:
        self._flush_paragraph()
        self._add_blank = True

    def _flush_paragraph(self) -> None:
        if self._add_blank:
            self._lines.append("")
            self._add_blank = False
        if len(self._current_paragraph) == 0:
            return
        paragraph = " ".join(self._current_paragraph)
        lines = wrap(paragraph, 80 - self._indent) if self._wrap else [paragraph]
        self._lines.extend([" " * self._indent + line for line in lines])
        self._current_paragraph = []

    def indented_line(self, content: str) -> None:
        with self.indented_block(blank_before=False, blank_after=False):
            self.newline(content)

    @contextmanager
    def indented_block(self, blank_before: bool = True, blank_after: bool = True) -> Iterator[None]:
        if blank_before:
            self.blank()
        self._flush_paragraph()
        self._indent += 4
        yield
        self._flush_paragraph()
        self._indent -= 4
        if blank_after:
            self.blank()

    def __str__(self) -> str:
        self._add_blank = False
        self._flush_paragraph()
        return "\n".join(self._lines)


class HelpfulException(Exception, ABC):
    def __str__(self) -> str:
        try:
            message = self.explanation()
            if len(message) > 0 and message[-1] == "\n":
                return message
            else:
                return message + "\n"
        except Exception as e:
            failsafe = self.failsafe_explanation()
            return "\n".join(
                (
                    failsafe,
                    "An error occurred when generating a more helpful error message:",
                    str(e),
                )
            )

    @abstractmethod
    def explanation(self) -> str:
        raise NotImplementedError()

    @abstractmethod
    def failsafe_explanation(self) -> str:
        raise NotImplementedError()


def qname(value: Any) -> str:
    return f"'{sname(value)}'"


def rname(resource: "BoundResource[Any]") -> str:
    from seamful.resource import ModuleResource, ProviderResource

    if isinstance(resource, ModuleResource):
        return f"{sname(resource.module)}.{resource.name}"
    elif isinstance(resource, ProviderResource):
        return f"{sname(resource.provider)}.{resource.name}"
    else:
        raise TypeError()


def rdef(resource: "BoundResource[Any]") -> str:
    from seamful.resource import ModuleResource, OverridingResource, PrivateResource

    if isinstance(resource, ModuleResource):
        return f"{sname(resource.module)}.{resource.name} = Resource({sname(resource.type)})"
    elif isinstance(resource, OverridingResource):
        return (
            f"{sname(resource.provider)}.{resource.name} = "
            f"Resource({sname(resource.type)}, ResourceKind.OVERRIDE)"
        )
    elif isinstance(resource, PrivateResource):
        return (
            f"{sname(resource.provider)}.{resource.name} = "
            f"Resource({sname(resource.type)}, ResourceKind.PRIVATE)"
        )
    else:
        raise TypeError()


def sname(value: type) -> str:
    if isinstance(value, type):
        return value.__name__
    else:
        return repr(value)


def fname(value: Any) -> str:
    if isinstance(value, type):
        return f"{value.__module__}.{sname(value)}"
    else:
        return str(value)


if sys.version_info < (3, 9):
    INCLUDE_DEFINITION_LINE = False
elif os.environ.get("SEAMFUL_DISABLE_ERROR_DEFINITION_LINE") == "1":
    INCLUDE_DEFINITION_LINE = False
else:
    INCLUDE_DEFINITION_LINE = True


def location(value: type) -> Optional[str]:
    root = Path(os.getcwd())
    module_filename = inspect.getsourcefile(value)
    if root is None or module_filename is None:
        return None
    path = Path(module_filename)
    relative = path.relative_to(root)
    if INCLUDE_DEFINITION_LINE:
        lineno = inspect.getsourcelines(value)[1]
        return f"{relative}:{lineno}"
    else:
        return str(relative)


def point_to_definition(value: type) -> Optional[str]:
    definition = location(value)
    return f'{sname(value)}: "{definition}"' if definition is not None else None
