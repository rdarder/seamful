import inspect
import logging
import os
from functools import wraps
from pathlib import Path
from typing import Callable, Any, Type, TypeVar, Tuple
from unittest import TestCase


class TestCaseWithOutputFixtures(TestCase):
    maxDiff = 10_000
    regenerate_fixtures: bool
    fixture_location: Path
    fixture_prefix: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.regenerate_fixtures = os.environ.get("REGENERATE_FIXTURES") is not None
        cls.fixture_location, cls.fixture_prefix = _get_fixture_location(cls)

    @classmethod
    def tearDownClass(cls) -> None:
        if not cls.regenerate_fixtures:
            return
        used_fixtures = {
            _get_fixture_path(cls, method)
            for _, method in inspect.getmembers(cls)
            if callable(method) and hasattr(method, "uses_fixtures")
        }
        existing_fixtures = set(cls.fixture_location.glob(f"{cls.fixture_prefix}_*.txt"))
        for extra_fixture in existing_fixtures - used_fixtures:
            logging.getLogger().warning(f"Removing unused fixture {extra_fixture}")
            extra_fixture.unlink()


T = TypeVar("T", bound=TestCaseWithOutputFixtures)


def validate_output_any_line_order(test_method: Callable[[T], Any]) -> Callable[[T], Any]:
    return _validate_output(test_method, line_order_matters=False)


def validate_output(test_method: Callable[[T], Any]) -> Callable[[T], Any]:
    return _validate_output(test_method, line_order_matters=True)


def _validate_output(
    test_method: Callable[[T], Any], line_order_matters: bool = True
) -> Callable[[T], Any]:
    @wraps(test_method)
    def validating_test_method(test: TestCaseWithOutputFixtures) -> None:
        if not hasattr(test, "fixture_location"):
            test.fail(
                "Missing fixture location. TestCase class probably not set up for fixture tests."
            )
        if test.regenerate_fixtures:
            return _generate_text_fixture_for_test_method(test, test_method, line_order_matters)

        test_returns = _run_test_and_ensure_returns_something(test, test_method)
        fixture_path = _get_fixture_path(test.__class__, test_method)
        if not fixture_path.exists():
            test.fail(f"Fixture {fixture_path} does not exist.")
        with open(fixture_path, "r") as fixture_file:
            loaded_fixture = fixture_file.read()
        if line_order_matters:
            test.assertEqual(loaded_fixture, str(test_returns))
        else:
            test.assertSetEqual(
                set(loaded_fixture.splitlines()), set(str(test_returns).splitlines())
            )

    setattr(validating_test_method, "uses_fixtures", True)
    return validating_test_method


V = TypeVar("V")


def _run_test_and_ensure_returns_something(test: TestCase, test_method: Callable[..., V]) -> V:
    test_returns = test_method(test)
    if test_returns is None:
        test.fail("Test case expected to return something, but returned None.")
    return test_returns


def _get_fixture_path(
    test: Type[TestCaseWithOutputFixtures], test_method: Callable[..., Any]
) -> Path:
    fixture_path = test.fixture_location.joinpath(
        f"{test.fixture_prefix}_{test_method.__name__}.txt"
    )
    return fixture_path


def _get_fixture_location(test: Type[TestCase]) -> Tuple[Path, str]:
    base = Path(inspect.getfile(test))
    location = base.parent.joinpath("test_fixtures")
    prefix = f"{base.stem}_{test.__name__}"
    return location, prefix


def _generate_text_fixture_for_test_method(
    test: TestCaseWithOutputFixtures, test_method: Callable[..., Any], line_order_matters: bool
) -> None:
    test_output = str(_run_test_and_ensure_returns_something(test, test_method))
    fixture_path = _get_fixture_path(test.__class__, test_method)
    if not fixture_path.parent.exists():
        fixture_path.parent.mkdir()
    if fixture_path.exists():
        with open(fixture_path, "r") as existing_fixture:
            contents = existing_fixture.read()
            if line_order_matters:
                if test_output == contents:
                    return
            else:
                if set(test_output.splitlines()) == set(contents.splitlines()):
                    return
            logging.getLogger().warning(f"Regenerating test fixture for {test.id()}")
    else:
        logging.getLogger().warning(f"Adding new test fixture for {test.id()}")
    with open(fixture_path, "w") as fixture_file:
        fixture_file.write(str(test_output))
