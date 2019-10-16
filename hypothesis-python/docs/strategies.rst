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
External Strategies
-------------------

Some packages provide strategies directly:

* :pypi:`hypothesis-fspaths` - strategy to generate filesystem paths.
* :pypi:`hypothesis-geojson` - strategy to generate `GeoJson <http://geojson.org/>`_.
* :pypi:`hs-dbus-signature` - strategy to generate arbitrary
  `D-Bus signatures <https://dbus.freedesktop.org>`_.
* :pypi:`hypothesis_sqlalchemy` - strategies to generate :pypi:`SQLAlchemy` objects.
* :pypi:`hypothesis-ros` - strategies to generate messages and parameters for the `Robot Operating System <https://www.ros.org/>`_.
* :pypi:`hypothesis-csv` - strategy to generate CSV files.
* :pypi:`hypothesis-networkx` - strategy to generate :pypi:`networkx` graphs.
* :pypi:`hypothesis-bio` - strategies for bioinformatics data, such as DNA, codons, FASTA, and FASTQ formats.
* :pypi:`hypothesmith` - strategy to generate syntatically-valid Python code.

Others provide a function to infer a strategy from some other schema:

* :pypi:`hypothesis-jsonschema` - infer strategies from `JSON schemas <https://json-schema.org/>`_.
* :pypi:`lollipop-hypothesis` - infer strategies from :pypi:`lollipop` schemas.
* :pypi:`hypothesis-drf` - infer strategies from a :pypi:`djangorestframework` serialiser.
* :pypi:`hypothesis-mongoengine` - infer strategies from a :pypi:`mongoengine` model.
* :pypi:`hypothesis-pb` - infer strategies from `Protocol Buffer
  <https://developers.google.com/protocol-buffers/>`_ schemas.


-----------------
Other Cool Things
-----------------

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
eqivalent, from function-level to register-transfer level and even to hardware.

:pypi:`libarchimedes` makes it easy to use Hypothesis in
`the Hy language <https://github.com/hylang/hy>`_, a Lisp embedded in Python.

:pypi:`battle_tested` is a fuzzing tool that will show you how your code can
fail - by trying all kinds of inputs and reporting whatever happens.

:pypi:`pytest-subtesthack` functions as a workaround for :issue:`377`.


--------------------
Writing an Extension
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
external dependencies just goes in hypothesis.extra.
