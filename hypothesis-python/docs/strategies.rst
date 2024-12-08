=============================
Projects extending Hypothesis
=============================

Hypothesis has been eagerly used and extended by the open source community.
This page lists extensions and applications; you can find more or newer
packages by searching PyPI `by keyword <https://pypi.org/search/?q=hypothesis>`_
or `filter by classifier <https://pypi.org/search/?c=Framework+%3A%3A+Hypothesis>`_,
or search `libraries.io <https://libraries.io/search?languages=Python&q=hypothesis>`_.

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

:pypi:`icontract-hypothesis` includes a :doc:`ghostwriter <ghostwriter>` for test files
and IDE integrations such as `icontract-hypothesis-vim <https://github.com/mristin/icontract-hypothesis-vim>`_,
`icontract-hypothesis-pycharm <https://github.com/mristin/icontract-hypothesis-pycharm>`_,
and
`icontract-hypothesis-vscode <https://github.com/mristin/icontract-hypothesis-vscode>`_ -
you can run a quick 'smoke test' with only a few keystrokes for any type-annotated
function, even if it doesn't have any contracts!

--------------------
Writing an extension
--------------------

*See* :gh-file:`CONTRIBUTING.rst` *for more information.*

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

--------------------------------------------------
Hypothesis integration via setuptools entry points
--------------------------------------------------

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

`Entry points <https://amir.rachum.com/blog/2017/07/28/python-entry-points/>`__
are Python's standard way of automating the latter: when you register a
``"hypothesis"`` entry point in your ``setup.py``, we'll import and run it
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

and then tell ``setuptools`` that this is your ``"hypothesis"`` entry point:

.. code-block:: python

    # setup.py

    # You can list a module to import by dotted name
    entry_points = {"hypothesis": ["_ = mymodule.a_submodule"]}

    # Or name a specific function too, and Hypothesis will call it for you
    entry_points = {"hypothesis": ["_ = mymodule:_hypothesis_setup_hook"]}

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

   EXPERIMENTAL AND UNSTABLE.

The importable name of a backend which Hypothesis should use to generate primitive
types.  We aim to support heuristic-random, solver-based, and fuzzing-based backends.

See :issue:`3086` for details, e.g. if you're interested in writing your own backend.
(note that there is *no stable interface* for this; you'd be helping us work out
what that should eventually look like, and we're likely to make regular breaking
changes for some time to come)

Using the prototype :pypi:`crosshair-tool` backend via :pypi:`hypothesis-crosshair`,
a solver-backed test might look something like:

.. code-block:: python

    from hypothesis import given, settings, strategies as st


    @settings(backend="crosshair")  # pip install hypothesis[crosshair]
    @given(st.integers())
    def test_needs_solver(x):
        assert x != 123456789
