# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

"""
The pytest plugin for Hypothesis.

We move this from the old location at `hypothesis.extra.pytestplugin` so that it
can be loaded by Pytest without importing Hypothesis.  In turn, this means that
Hypothesis will not load our own third-party plugins (with associated side-effects)
unless and until the user explicitly runs `import hypothesis`.

See https://github.com/HypothesisWorks/hypothesis/issues/3140 for details.
"""

import base64
import json
import os
import sys
import warnings
from inspect import signature

import _hypothesis_globals
import pytest

try:
    from _pytest.junitxml import xml_key
except ImportError:
    xml_key = "_xml"  # type: ignore

LOAD_PROFILE_OPTION = "--hypothesis-profile"
VERBOSITY_OPTION = "--hypothesis-verbosity"
PRINT_STATISTICS_OPTION = "--hypothesis-show-statistics"
SEED_OPTION = "--hypothesis-seed"
EXPLAIN_OPTION = "--hypothesis-explain"

_VERBOSITY_NAMES = ["quiet", "normal", "verbose", "debug"]
_ALL_OPTIONS = [
    LOAD_PROFILE_OPTION,
    VERBOSITY_OPTION,
    PRINT_STATISTICS_OPTION,
    SEED_OPTION,
    EXPLAIN_OPTION,
]
_FIXTURE_MSG = """Function-scoped fixture {0!r} used by {1!r}

TODO rewrite with whatever we want to warn about
"""

STATS_KEY = "_hypothesis_stats"
FAILING_EXAMPLES_KEY = "_hypothesis_failing_examples"


class StoringReporter:
    def __init__(self, config):
        assert "hypothesis" in sys.modules
        from hypothesis.reporting import default

        self.report = default
        self.config = config
        self.results = []

    def __call__(self, msg):
        if self.config.getoption("capture", "fd") == "no":
            self.report(msg)
        if not isinstance(msg, str):
            msg = repr(msg)
        self.results.append(msg)


_item_scoped_fixtures = set([
    # The ones below are never processed anyway, not being present in the
    # fixture closure, but setting them here makes it not-an-error to use
    # them as argument names when registering via @item_scoped.
    "request",  # pseudofixture, but also naturally item-scoped
    "self",  # non-fixture (bound) arg
])

# Avoiding distutils.version.LooseVersion due to
# https://github.com/HypothesisWorks/hypothesis/issues/2490
if tuple(map(int, pytest.__version__.split(".")[:2])) < (4, 6):  # pragma: no cover
    import warnings

    PYTEST_TOO_OLD_MESSAGE = """
        You are using pytest version %s. Hypothesis tests work with any test
        runner, but our pytest plugin requires pytest 4.6 or newer.
        Note that the pytest developers no longer support your version either!
        Disabling the Hypothesis pytest plugin...
    """
    warnings.warn(PYTEST_TOO_OLD_MESSAGE % (pytest.__version__,), stacklevel=1)

else:
    # Restart side-effect detection as early as possible, to maximize coverage. We
    # need balanced increment/decrement in configure/sessionstart to support nested
    # pytest (e.g. runpytest_inprocess), so this early increment in effect replaces
    # the first one in pytest_configure.
    if not os.environ.get("HYPOTHESIS_EXTEND_INITIALIZATION"):
        _hypothesis_globals.in_initialization += 1
        if "hypothesis" in sys.modules:
            # Some other plugin has imported hypothesis, so we'll check if there
            # have been undetected side-effects and warn if so.
            from hypothesis.configuration import notice_initialization_restarted

            notice_initialization_restarted()

    def pytest_addoption(parser):
        group = parser.getgroup("hypothesis", "Hypothesis")
        group.addoption(
            LOAD_PROFILE_OPTION,
            action="store",
            help="Load in a registered hypothesis.settings profile",
        )
        group.addoption(
            VERBOSITY_OPTION,
            action="store",
            choices=_VERBOSITY_NAMES,
            help="Override profile with verbosity setting specified",
        )
        group.addoption(
            PRINT_STATISTICS_OPTION,
            action="store_true",
            help="Configure when statistics are printed",
            default=False,
        )
        group.addoption(
            SEED_OPTION,
            action="store",
            help="Set a seed to use for all Hypothesis tests",
        )
        group.addoption(
            EXPLAIN_OPTION,
            action="store_true",
            help="Enable the `explain` phase for failing Hypothesis tests",
            default=False,
        )

    def _any_hypothesis_option(config):
        return bool(any(config.getoption(opt) for opt in _ALL_OPTIONS))

    def pytest_report_header(config):
        if not (
            config.option.verbose >= 1
            or "hypothesis" in sys.modules
            or _any_hypothesis_option(config)
        ):
            return None

        from hypothesis import Verbosity, settings

        if config.option.verbose < 1 and settings.default.verbosity < Verbosity.verbose:
            return None
        settings_str = settings.default.show_changed()
        if settings_str != "":
            settings_str = f" -> {settings_str}"
        return f"hypothesis profile {settings._current_profile!r}{settings_str}"

    def pytest_configure(config):
        config.addinivalue_line("markers", "hypothesis: Tests which use hypothesis.")
        if not _any_hypothesis_option(config):
            return
        from hypothesis import Phase, Verbosity, core, settings

        profile = config.getoption(LOAD_PROFILE_OPTION)
        if profile:
            settings.load_profile(profile)
        verbosity_name = config.getoption(VERBOSITY_OPTION)
        if verbosity_name and verbosity_name != settings.default.verbosity.name:
            verbosity_value = Verbosity[verbosity_name]
            name = f"{settings._current_profile}-with-{verbosity_name}-verbosity"
            # register_profile creates a new profile, exactly like the current one,
            # with the extra values given (in this case 'verbosity')
            settings.register_profile(name, verbosity=verbosity_value)
            settings.load_profile(name)
        if (
            config.getoption(EXPLAIN_OPTION)
            and Phase.explain not in settings.default.phases
        ):
            name = f"{settings._current_profile}-with-explain-phase"
            phases = (*settings.default.phases, Phase.explain)
            settings.register_profile(name, phases=phases)
            settings.load_profile(name)

        seed = config.getoption(SEED_OPTION)
        if seed is not None:
            try:
                seed = int(seed)
            except ValueError:
                pass
            core.global_force_seed = seed

    def _reset_function_scoped_fixtures(request):
        """Can be called by an external subtest runner to reset function scoped
        fixtures in-between function calls within a single test item."""
        from _pytest.compat import NOTSET
        from _pytest.scope import Scope
        from _pytest.fixtures import SubRequest
        self = request  # because prototyped inside _pytest.FixtureRequest

        info = self._fixturemanager.getfixtureinfo(
            node=self._pyfuncitem, func=self._pyfuncitem.function, cls=None
        )

        # Build a safe traversal order where dependencies are always processed
        # before any dependents. (info.names_closure is not sufficient)
        # TODO: cache this traversal order, and name2fixturedefs?
        deps_per_name = {}
        for fixture_name, fixture_defs in info.name2fixturedefs.items():
            deps = deps_per_name[fixture_name] = set()
            for fixturedef in fixture_defs:
                deps |= set(fixturedef.argnames) & info.name2fixturedefs.keys()
            deps -= {fixture_name}
        traversal_order = []
        while deps_per_name:
            to_remove = set(name for name, deps in deps_per_name.items() if not deps)
            traversal_order += to_remove
            if not to_remove:
                # We're stuck in a cyclic dependency. This can actually happen in
                # practice, due to incomplete dependency graph for fixtures with same
                # name at different levels. Plain pytest seems to resolve this somewhat
                # arbitrarily (ref tests/pytest/test_cyclic_fixture_dependency), but
                # that resolution is unavailable to us?
                # Maybe we should just return here without any action, and make it
                # a healthcheck error.
                assert to_remove, "can't resolve cyclic fixture dependency"
            deps_per_name = {
                k: v - to_remove for k, v in deps_per_name.items() if k not in to_remove
            }

        context = self._fixture_defs.copy()
        for k in traversal_order:
            # this isn't strictly necessary, but safeguards against leaking stale
            # state into the new fixture values if the traversal order is bad
            del context[k]

        for fixture_name in traversal_order:
            fixture_defs = info.name2fixturedefs[fixture_name]

            if fixture_name in _item_scoped_fixtures:
                context[fixture_name] = fixture_defs[-1]
                continue

            # cargo-culted from _pytest.fixtures
            callspec = getattr(self._pyfuncitem, "callspec", None)
            if callspec is not None and fixture_name in callspec.params:
                param = callspec.params[fixture_name]
                param_index = callspec.indices[fixture_name]
                # The parametrize invocation scope overrides the fixture's scope.
                scope = callspec._arg2scope[fixture_name]
            else:
                param = NOTSET
                param_index = 0
                scope = None

            for fixturedef in fixture_defs:
                if param is NOTSET:
                    scope = fixturedef._scope
                if scope is Scope.Function:
                    subrequest = SubRequest(
                        self, scope, param, param_index, fixturedef, _ispytest=True
                    )
                    subrequest._fixture_defs = context

                    # ...and reset! Note that finish(...) will invalidate also
                    # dependent fixtures, so many of the later ones are no-ops.
                    fixturedef.finish(subrequest)
                    fixturedef.execute(subrequest)

                    # this ensures all dependencies of the fixture are available to
                    # the next subrequest (as a consequence of the safe traversal order)
                    context[fixture_name] = fixturedef

        for fixture_name in self._pyfuncitem.funcargs.keys() & context.keys():
            fixture_val = self.getfixturevalue(fixture_name)
            self._pyfuncitem.funcargs[fixture_name] = fixture_val

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_call(item):
        __tracebackhide__ = True
        if not (hasattr(item, "obj") and "hypothesis" in sys.modules):
            yield
            return

        from hypothesis import core
        from hypothesis.internal.detection import is_hypothesis_test

        # See https://github.com/pytest-dev/pytest/issues/9159
        core.pytest_shows_exceptiongroups = (
            getattr(pytest, "version_tuple", ())[:2] >= (7, 2)
            or item.config.getoption("tbstyle", "auto") == "native"
        )
        core.running_under_pytest = True

        if not is_hypothesis_test(item.obj):
            # If @given was not applied, check whether other hypothesis
            # decorators were applied, and raise an error if they were.
            # We add this frame of indirection to enable __tracebackhide__.
            def raise_hypothesis_usage_error(msg):
                raise InvalidArgument(msg)

            if getattr(item.obj, "is_hypothesis_strategy_function", False):
                from hypothesis.errors import InvalidArgument

                raise_hypothesis_usage_error(
                    f"{item.nodeid} is a function that returns a Hypothesis strategy, "
                    "but pytest has collected it as a test function.  This is useless "
                    "as the function body will never be executed.  To define a test "
                    "function, use @given instead of @composite."
                )
            message = "Using `@%s` on a test without `@given` is completely pointless."
            for name, attribute in [
                ("example", "hypothesis_explicit_examples"),
                ("seed", "_hypothesis_internal_use_seed"),
                ("settings", "_hypothesis_internal_settings_applied"),
                ("reproduce_example", "_hypothesis_internal_use_reproduce_failure"),
            ]:
                if hasattr(item.obj, attribute):
                    from hypothesis.errors import InvalidArgument

                    raise_hypothesis_usage_error(message % (name,))
            yield
        else:
            from hypothesis import HealthCheck, settings as Settings
            from hypothesis.internal.escalation import current_pytest_item
            from hypothesis.internal.healthcheck import fail_health_check
            from hypothesis.reporting import with_reporter
            from hypothesis.statistics import collector, describe_statistics

            # Retrieve the settings for this test from the test object, which
            # is normally a Hypothesis wrapped_test wrapper. If this doesn't
            # work, the test object is probably something weird
            # (e.g a stateful test wrapper), so we skip the function-scoped
            # fixture check.
            settings = getattr(
                item.obj, "_hypothesis_internal_use_settings", Settings.default
            )

            parametrized_fixture = False
            functionscoped_fixture = False
            transitive_fixtures = set()
            reused_fixture_names = set()
            info = item._request._fixturemanager.getfixtureinfo(
                node=item, func=item.function, cls=None
            )
            for fx_name, fx_defs in info.name2fixturedefs.items():
                if len(fx_defs) > 1:
                    reused_fixture_names.add(fx_name)
                for fx in fx_defs:
                    functionscoped_fixture |= (
                        fx.scope == "function" and fx_name not in _item_scoped_fixtures
                    )
                    parametrized_fixture |= bool(fx.params)
                    if functionscoped_fixture:
                        transitive_fixtures |= set(fx.argnames) - {fx_name}

            if (reused_transitive := transitive_fixtures & reused_fixture_names):
                if True:
                    # currently more precisely caught as a cyclic dependency, but
                    # remains a TODO to figure out precise limitations
                    pass
                elif (
                        HealthCheck.function_scoped_fixture
                        in settings.suppress_health_check
                ):
                    functionscoped_fixture = False
                else:
                    fail_health_check(
                        settings,
                        _FIXTURE_MSG.format(list(reused_transitive)[0], item.nodeid),
                        HealthCheck.function_scoped_fixture,
                    )

            if parametrized_fixture or (item.get_closest_marker("parametrize") is not None):
                # Disable the differing_executors health check due to false alarms:
                # see https://github.com/HypothesisWorks/hypothesis/issues/3733
                from hypothesis import settings as Settings

                fn = getattr(item.obj, "__func__", item.obj)
                fn._hypothesis_internal_use_settings = Settings(
                    parent=settings,
                    suppress_health_check={HealthCheck.differing_executors}
                    | set(settings.suppress_health_check),
                )

                # Give every parametrized test invocation a unique database key
                key = item.nodeid.encode()
                item.obj.hypothesis.inner_test._hypothesis_internal_add_digest = key

            if functionscoped_fixture and hasattr(item.obj, "hypothesis"):
                # Stateful tests don't have this attribute, but that's fine
                # as there's no expectation of resetting autouse fixtures
                # for rule executions.
                def reset():
                    _reset_function_scoped_fixtures(item._request)
                    return item.funcargs
                item.obj.hypothesis.inner_test._hypothesis_internal_reset_fixtures = reset

            store = StoringReporter(item.config)

            def note_statistics(stats):
                stats["nodeid"] = item.nodeid
                item.hypothesis_statistics = describe_statistics(stats)

            with collector.with_value(note_statistics):
                with with_reporter(store):
                    with current_pytest_item.with_value(item):
                        yield
            if store.results:
                item.hypothesis_report_information = list(store.results)

    def _stash_get(config, key, default):
        if hasattr(config, "stash"):
            # pytest 7
            return config.stash.get(key, default)
        elif hasattr(config, "_store"):
            # pytest 5.4
            return config._store.get(key, default)
        else:
            return getattr(config, key, default)

    @pytest.hookimpl(hookwrapper=True)
    def pytest_runtest_makereport(item, call):
        report = (yield).get_result()
        if hasattr(item, "hypothesis_report_information"):
            report.sections.append(
                ("Hypothesis", "\n".join(item.hypothesis_report_information))
            )
        if report.when != "teardown":
            return

        terminalreporter = item.config.pluginmanager.getplugin("terminalreporter")

        if hasattr(item, "hypothesis_statistics"):
            stats = item.hypothesis_statistics
            stats_base64 = base64.b64encode(stats.encode()).decode()

            name = "hypothesis-statistics-" + item.nodeid

            # Include hypothesis information to the junit XML report.
            #
            # Note that when `pytest-xdist` is enabled, `xml_key` is not present in the
            # stash, so we don't add anything to the junit XML report in that scenario.
            # https://github.com/pytest-dev/pytest/issues/7767#issuecomment-1082436256
            xml = _stash_get(item.config, xml_key, None)
            if xml:
                xml.add_global_property(name, stats_base64)

            # If there's a terminal report, include our summary stats for each test
            if terminalreporter is not None:
                report.__dict__[STATS_KEY] = stats

            # If there's an HTML report, include our summary stats for each test
            pytest_html = item.config.pluginmanager.getplugin("html")
            if pytest_html is not None:  # pragma: no cover
                report.extra = [
                    *getattr(report, "extra", []),
                    pytest_html.extras.text(stats, name="Hypothesis stats"),
                ]

        # This doesn't intrinsically have anything to do with the terminalreporter;
        # we're just cargo-culting a way to get strings back to a single function
        # even if the test were distributed with pytest-xdist.
        failing_examples = getattr(item, FAILING_EXAMPLES_KEY, None)
        if failing_examples and terminalreporter is not None:
            try:
                from hypothesis.extra._patching import FAIL_MSG, get_patch_for
            except ImportError:
                return
            # We'll save this as a triple of [filename, hunk_before, hunk_after].
            triple = get_patch_for(item.obj, [(x, FAIL_MSG) for x in failing_examples])
            if triple is not None:
                report.__dict__[FAILING_EXAMPLES_KEY] = json.dumps(triple)

    def pytest_terminal_summary(terminalreporter):
        failing_examples = []
        print_stats = terminalreporter.config.getoption(PRINT_STATISTICS_OPTION)
        if print_stats:
            terminalreporter.section("Hypothesis Statistics")
        for reports in terminalreporter.stats.values():
            for report in reports:
                stats = report.__dict__.get(STATS_KEY)
                if stats and print_stats:
                    terminalreporter.write_line(stats + "\n\n")
                fex = report.__dict__.get(FAILING_EXAMPLES_KEY)
                if fex:
                    failing_examples.append(json.loads(fex))

        from hypothesis.internal.observability import _WROTE_TO

        if _WROTE_TO:
            terminalreporter.section("Hypothesis")
            for fname in sorted(_WROTE_TO):
                terminalreporter.write_line(f"observations written to {fname}")

        if failing_examples:
            # This must have been imported already to write the failing examples
            from hypothesis.extra._patching import gc_patches, make_patch, save_patch

            patch = make_patch(failing_examples)
            try:
                gc_patches()
                fname = save_patch(patch)
            except Exception:
                # fail gracefully if we hit any filesystem or permissions problems
                return
            if not _WROTE_TO:
                terminalreporter.section("Hypothesis")
            terminalreporter.write_line(
                f"`git apply {fname}` to add failing examples to your code."
            )

    def pytest_collection_modifyitems(items):
        if "hypothesis" not in sys.modules:
            return

        from hypothesis.internal.detection import is_hypothesis_test

        for item in items:
            if isinstance(item, pytest.Function) and is_hypothesis_test(item.obj):
                item.add_marker("hypothesis")

    def pytest_sessionstart(session):
        # Note: may be called multiple times, so we can go negative
        _hypothesis_globals.in_initialization -= 1

    # Monkeypatch some internals to prevent applying @pytest.fixture() to a
    # function which has already been decorated with @hypothesis.given().
    # (the reverse case is already an explicit error in Hypothesis)
    # We do this here so that it catches people on old Pytest versions too.
    from _pytest import fixtures

    def _ban_given_call(self, function):
        if "hypothesis" in sys.modules:
            from hypothesis.internal.detection import is_hypothesis_test

            if is_hypothesis_test(function):
                raise RuntimeError(
                    f"Can't apply @pytest.fixture() to {function.__name__} because "
                    "it is already decorated with @hypothesis.given()"
                )
        return _orig_call(self, function)

    _orig_call = fixtures.FixtureFunctionMarker.__call__
    fixtures.FixtureFunctionMarker.__call__ = _ban_given_call  # type: ignore


def item_scoped(fn):
    import inspect
    from hypothesis.errors import InvalidArgument

    # Just simple checking, as this is an advanced niche feature. We should
    # in principle allow class-scoped and above, but that test would have to
    # be performed at call-time. Better to add a new scope to pytest.
    for arg in inspect.getargs(fn.__code__).args:
        if arg not in _item_scoped_fixtures:
            raise InvalidArgument(
                f"Item-scoped fixture `{fn.__name__}` has a dependency on another "
                f" fixture `{arg}`. This is currently only allowed if {arg} is "
                "also marked as item scope. (Marking as item scope is a no-op for "
                "scopes wider than function.)"
            )
    _item_scoped_fixtures.add(fn.__name__)
    return fn


@pytest.fixture(scope="function")
@item_scoped
def monkeypatch_item():
    with pytest.MonkeyPatch.context() as monkeypatch:
        yield monkeypatch


def load():
    """Required for `pluggy` to load a plugin from setuptools entrypoints."""
