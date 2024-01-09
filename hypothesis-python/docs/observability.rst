===================
Observability tools
===================

.. warning::

    This feature is experimental, and could have breaking changes or even be removed
    without notice.  Try it out, let us know what you think, but don't rely on it
    just yet!


Motivation
==========

Understanding what your code is doing - for example, why your test failed - is often
a frustrating exercise in adding some more instrumentation or logging (or ``print()`` calls)
and running it again.  The idea of :wikipedia:`observability <Observability_(software)>`
is to let you answer questions you didn't think of in advance.  In slogan form,

  *Debugging should be a data analysis problem.*

By default, Hypothesis only reports the minimal failing example... but sometimes you might
want to know something about *all* the examples.  Printing them to the terminal with
:ref:`verbose output <verbose-output>` might be nice, but isn't always enough.
This feature gives you an analysis-ready dataframe with useful columns and one row
per test case, with columns from arguments to code coverage to pass/fail status.

This is deliberately a much lighter-weight and task-specific system than e.g.
`OpenTelemetry <https://opentelemetry.io/>`__.  It's also less detailed than time-travel
debuggers such as `rr <https://rr-project.org/>`__ or `pytrace <https://pytrace.com/>`__,
because there's no good way to compare multiple traces from these tools and their
Python support is relatively immature.


Configuration
=============

If you set the ``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY`` environment variable,
Hypothesis will log various observations to jsonlines files in the
``.hypothesis/observed/`` directory.  You can load and explore these with e.g.
:func:`pd.read_json(".hypothesis/observed/*_testcases.jsonl", lines=True) <pandas.read_json>`,
or by using the :pypi:`sqlite-utils` and :pypi:`datasette` libraries::

    sqlite-utils insert testcases.db testcases .hypothesis/observed/*_testcases.jsonl --nl --flatten
    datasette serve testcases.db

If you are experiencing a significant slow-down, you can try setting
``HYPOTHESIS_EXPERIMENTAL_OBSERVABILITY_NOCOVER`` instead; this will disable coverage information
collection. This should not be necessary on Python 3.12 or later.


Collecting more information
---------------------------

If you want to record more information about your test cases than the arguments and
outcome - for example, was ``x`` a binary tree?  what was the difference between the
expected and the actual value?  how many queries did it take to find a solution? -
Hypothesis makes this easy.

:func:`~hypothesis.event` accepts a string label, and optionally a string or int or
float observation associated with it.  All events are collected and summarized in
:ref:`statistics`, as well as included on a per-test-case basis in our observations.

:func:`~hypothesis.target` is a special case of numeric-valued events: as well as
recording them in observations, Hypothesis will try to maximize the targeted value.
Knowing that, you can use this to guide the search for failing inputs.


Data Format
===========

We dump observations in `json lines format <https://jsonlines.org/>`__, with each line
describing either a test case or an information message.  The tables below are derived
from :download:`this machine-readable JSON schema <schema_observations.json>`, to
provide both readable and verifiable specifications.

Note that we use :func:`python:json.dumps` and can therefore emit non-standard JSON
which includes infinities and NaN.  This is valid in `JSON5 <https://json5.org/>`__,
and supported by `some JSON parsers <https://evanhahn.com/pythons-nonstandard-json-encoding/>`__
including Gson in Java, ``JSON.parse()`` in Ruby, and of course in Python.

.. jsonschema:: ./schema_observations.json#/oneOf/0
   :hide_key: /additionalProperties, /type
.. jsonschema:: ./schema_observations.json#/oneOf/1
   :hide_key: /additionalProperties, /type
