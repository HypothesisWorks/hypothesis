RELEASE_TYPE: minor

Hypothesis now supports loading settings from a ``hypothesis.ini`` configuration
file! This allows you to define :doc:`settings profiles <settings>` using
standard INI format without writing Python code.

Create a ``hypothesis.ini`` file in your project root (the directory containing
``.git/``, ``setup.py``, ``pyproject.toml``, or similar project markers):

.. code-block:: ini

    [hypothesis]
    max_examples = 200
    deadline = 500

    [hypothesis:ci]
    max_examples = 1000
    deadline = None
    derandomize = true

The ``[hypothesis]`` section configures the default profile, while
``[hypothesis:profile_name]`` sections define named profiles. Settings from
``hypothesis.ini`` have priority over built-in defaults but are overridden by
explicit :func:`@settings() <hypothesis.settings>` decorators on individual tests.

See the :doc:`settings tutorial <settings>` for complete documentation including
supported value types, auto-loading profiles, and configuration priority.

Thanks to tboy1337 for this feature!
