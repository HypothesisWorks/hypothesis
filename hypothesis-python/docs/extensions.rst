======================
Third-party extensions
======================

There are a number of open-source community libraries that extend Hypothesis. This page lists some of them; you can find more by searching PyPI `by keyword <https://pypi.org/search/?q=hypothesis>`_ or `by framework classifier <https://pypi.org/search/?c=Framework+%3A%3A+Hypothesis>`_.

If there's something missing which you think should be here, let us know!

.. note::
    Being listed on this page does not imply that the Hypothesis
    maintainers endorse a package.

-------------------
External strategies
-------------------

Some packages provide strategies directly:

* :pypi:`hypothesis-fspaths` - strategy to generate filesystem paths.
* :pypi:`hypothesis-geojson` - strategy to generate `GeoJson <https://geojson.org/>`_.
* :pypi:`hypothesis-geometry` - strategies to generate geometric objects.
* :pypi:`hs-dbus-signature` - strategy to generate arbitrary
  `D-Bus signatures <https://www.freedesktop.org/wiki/Software/dbus/>`_.
* :pypi:`hypothesis-sqlalchemy` - strategies to generate :pypi:`SQLAlchemy` objects.
* :pypi:`hypothesis-ros` - strategies to generate messages and parameters for the `Robot Operating System <https://www.ros.org/>`_.
* :pypi:`hypothesis-csv` - strategy to generate CSV files.
* :pypi:`hypothesis-networkx` - strategy to generate :pypi:`networkx` graphs.
* :pypi:`hypothesis-bio` - strategies for bioinformatics data, such as DNA, codons, FASTA, and FASTQ formats.
* :pypi:`hypothesis-rdkit` - strategies to generate RDKit molecules and representations such as SMILES and mol blocks
* :pypi:`hypothesmith` - strategy to generate syntatically-valid Python code.
* :pypi:`hypothesis-torch` - strategy to generate various `Pytorch <https://pytorch.org/>`_ structures (including tensors and modules).

Others provide a function to infer a strategy from some other schema:

* :pypi:`hypothesis-jsonschema` - infer strategies from `JSON schemas <https://json-schema.org/>`_.
* :pypi:`lollipop-hypothesis` - infer strategies from :pypi:`lollipop` schemas.
* :pypi:`hypothesis-drf` - infer strategies from a :pypi:`djangorestframework` serialiser.
* :pypi:`hypothesis-graphql` - infer strategies from `GraphQL schemas <https://graphql.org/>`_.
* :pypi:`hypothesis-mongoengine` - infer strategies from a :pypi:`mongoengine` model.
* :pypi:`hypothesis-pb` - infer strategies from `Protocol Buffer
  <https://protobuf.dev/>`_ schemas.

Or some other custom integration, such as a :ref:`"hypothesis" entry point <entry-points>`:

* :pypi:`deal` is a design-by-contract library with built-in Hypothesis support.
* :pypi:`icontract-hypothesis` infers strategies from :pypi:`icontract` code contracts.
* :pypi:`pandera` schemas all have a ``.strategy()`` method, which returns a strategy for
  matching :class:`~pandas:pandas.DataFrame`\ s.
* :pypi:`Pydantic <pydantic>` automatically registers constrained types - so
  :func:`~hypothesis.strategies.builds` and :func:`~hypothesis.strategies.from_type`
  "just work" regardless of the underlying implementation.

-----------------
Other cool things
-----------------

`Tyche <https://marketplace.visualstudio.com/items?itemName=HarrisonGoldstein.tyche>`__
(`source <https://github.com/tyche-pbt>`__) is a VSCode extension which provides live
insights into your property-based tests, including the distribution of generated inputs
and the resulting code coverage.  You can `read the research paper here
<https://harrisongoldste.in/papers/uist23.pdf>`__.

:pypi:`schemathesis` is a tool for testing web applications built with `Open API / Swagger specifications <https://swagger.io/>`_.
It reads the schema and generates test cases which will ensure that the application is compliant with its schema.
The application under test could be written in any language, the only thing you need is a valid API schema in a supported format.
Includes CLI and convenient :pypi:`pytest` integration.
Powered by Hypothesis and :pypi:`hypothesis-jsonschema`, inspired by the earlier :pypi:`swagger-conformance` library.

`Trio <https://trio.readthedocs.io/>`_ is an async framework with "an obsessive
focus on usability and correctness", so naturally it works with Hypothesis!
:pypi:`pytest-trio` includes :ref:`a custom hook <custom-function-execution>`
that allows ``@given(...)`` to work with Trio-style async test functions, and
:pypi:`hypothesis-trio` includes stateful testing extensions to support
concurrent programs.

:pypi:`pymtl3` is "an open-source Python-based hardware generation, simulation,
and verification framework with multi-level hardware modeling support", which
ships with Hypothesis integrations to check that all of those levels are
equivalent, from function-level to register-transfer level and even to hardware.

:pypi:`libarchimedes` makes it easy to use Hypothesis in
`the Hy language <https://github.com/hylang/hy>`_, a Lisp embedded in Python.

:pypi:`battle-tested` is a fuzzing tool that will show you how your code can
fail - by trying all kinds of inputs and reporting whatever happens.

:pypi:`pytest-subtesthack` functions as a workaround for :issue:`377`.

:pypi:`returns` uses Hypothesis to verify that Higher Kinded Types correctly
implement functor, applicative, monad, and other laws; allowing a declarative
approach to be combined with traditional pythonic code.

:pypi:`icontract-hypothesis` includes a :ref:`ghostwriter <ghostwriter>` for test files
and IDE integrations such as `icontract-hypothesis-vim <https://github.com/mristin/icontract-hypothesis-vim>`_,
`icontract-hypothesis-pycharm <https://github.com/mristin/icontract-hypothesis-pycharm>`_,
and
`icontract-hypothesis-vscode <https://github.com/mristin/icontract-hypothesis-vscode>`_ -
you can run a quick 'smoke test' with only a few keystrokes for any type-annotated
function, even if it doesn't have any contracts!

--------------------
Writing an extension
--------------------

.. note::

    See :gh-file:`CONTRIBUTING.rst` for more information.

New strategies can be added to Hypothesis, or published as an external package
on PyPI - either is fine for most strategies. If in doubt, ask!

It's generally much easier to get things working outside, because there's more
freedom to experiment and fewer requirements in stability and API style. We're
happy to review and help with external packages as well as pull requests!

If you're thinking about writing an extension, please name it
``hypothesis-{something}`` - a standard prefix makes the community more
visible and searching for extensions easier.  And make sure you use the
``Framework :: Hypothesis`` trove classifier!

On the other hand, being inside gets you access to some deeper implementation
features (if you need them) and better long-term guarantees about maintenance.
We particularly encourage pull requests for new composable primitives that
make implementing other strategies easier, or for widely used types in the
standard library. Strategies for other things are also welcome; anything with
external dependencies just goes in ``hypothesis.extra``.

Tools such as assertion helpers may also need to check whether the current
test is using Hypothesis:

.. autofunction:: hypothesis.currently_in_test_context


.. _entry-points:

---------------------------------------
Hypothesis integration via entry points
---------------------------------------

If you would like to ship Hypothesis strategies for a custom type - either as
part of the upstream library, or as a third-party extension, there's a catch:
:func:`~hypothesis.strategies.from_type` only works after the corresponding
call to :func:`~hypothesis.strategies.register_type_strategy`, and you'll have
the same problem with :func:`~hypothesis.register_random`.  This means that
either

- you have to try importing Hypothesis to register the strategy when *your*
  library is imported, though that's only useful at test time, or
- the user has to call a 'register the strategies' helper that you provide
  before running their tests

`Entry points <https://setuptools.pypa.io/en/latest/userguide/entry_point.html>`__
are Python's standard way of automating the latter: when you register a
``"hypothesis"`` entry point in your ``pyproject.toml``, we'll import and run it
automatically when *hypothesis* is imported.  Nothing happens unless Hypothesis
is already in use, and it's totally seamless for downstream users!

Let's look at an example.  You start by adding a function somewhere in your
package that does all the Hypothesis-related setup work:

.. code-block:: python

    # mymodule.py

    class MyCustomType:
        def __init__(self, x: int):
            assert x >= 0, f"got {x}, but only positive numbers are allowed"
            self.x = x

    def _hypothesis_setup_hook():
        import hypothesis.strategies as st

        st.register_type_strategy(MyCustomType, st.integers(min_value=0))

and then declare this as your ``"hypothesis"`` entry point:

.. code-block:: toml

    # pyproject.toml

    # You can list a module to import by dotted name
    [project.entry-points.hypothesis]
    _ = "mymodule.a_submodule"

    # Or name a specific function, and Hypothesis will call it for you
    [project.entry-points.hypothesis]
    _ = "mymodule:_hypothesis_setup_hook"

And that's all it takes!

.. envvar:: HYPOTHESIS_NO_PLUGINS

   If set, disables automatic loading of all hypothesis plugins. This is probably only
   useful for our own self-tests, but documented in case it might help narrow down
   any particularly weird bugs in complex environments.


Interaction with :pypi:`pytest-cov`
-----------------------------------

Because pytest does not load plugins from entrypoints in any particular order,
using the Hypothesis entrypoint may import your module before :pypi:`pytest-cov`
starts.  `This is a known issue <https://github.com/pytest-dev/pytest/issues/935>`__,
but there are workarounds.

You can use :command:`coverage run pytest ...` instead of :command:`pytest --cov ...`,
opting out of the pytest plugin entirely.  Alternatively, you can ensure that Hypothesis
is loaded after coverage measurement is started by disabling the entrypoint, and
loading our pytest plugin from your ``conftest.py`` instead::

    echo "pytest_plugins = ['hypothesis.extra.pytestplugin']\n" > tests/conftest.py
    pytest -p "no:hypothesispytest" ...

Another alternative, which we in fact use in our CI self-tests because it works
well also with parallel tests, is to automatically start coverage early for all
new processes if an environment variable is set.
This automatic starting is set up by the PyPi package :pypi:`coverage_enable_subprocess`.

This means all configuration must be done in ``.coveragerc``, and not on the
command line::

    [run]
    parallel = True
    source = ...

Then, set the relevant environment variable and run normally::

    python -m pip install coverage_enable_subprocess
    export COVERAGE_PROCESS_START=$PATH/.coveragerc
    pytest [-n auto] ...
    coverage combine
    coverage report


.. _alternative-backends:

-----------------------------------
Alternative backends for Hypothesis
-----------------------------------

.. warning::

   Alternative backends are experimental and not yet part of the public API.
   We may continue to make breaking changes as we finalize the interface.

Hypothesis supports alternative backends, which tells Hypothesis how to generate primitive
types. This enables powerful generation techniques which are compatible with all parts of
Hypothesis, including the database and shrinking.

Hypothesis includes the following backends:

hypothesis
    The default backend.
hypothesis-urandom
    The same as the default backend, but uses ``/dev/urandom`` to back the randomness
    behind its PRNG. The only reason to use this backend over the default is if you are also
    using `Antithesis <https://antithesis.com/>`_, in which case this enables Antithesis
    mutations to drive Hypothesis generation.

    ``/dev/urandom`` is not available on Windows, so we emit a warning and fall back to the
    hypothesis backend there.
crosshair
    Generates examples using SMT solvers like z3, which is particularly effective at satisfying
    difficult checks in your code, like ``if`` or ``==`` statements.

    Requires ``pip install hypothesis[crosshair]``.

You can change the backend for a test with the ``backend`` setting. For instance, after
``pip install hypothesis[crosshair]``, you can use :pypi:`crosshair <crosshair-tool>` to
generate examples with SMT via the :pypi:`hypothesis-crosshair` backend:

.. code-block:: python

    from hypothesis import given, settings, strategies as st

    @settings(backend="crosshair")  # pip install hypothesis[crosshair]
    @given(st.integers())
    def test_needs_solver(x):
        assert x != 123456789

Failures found by alternative backends are saved to the database and shrink just like normally
generated examples, and in general interact with every feature of Hypothesis as you would expect.
