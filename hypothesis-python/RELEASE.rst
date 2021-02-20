RELEASE_TYPE: minor

The Hypothesis :pypi:`pytest` plugin now requires pytest version 4.6 or later.
If the plugin detects an earlier version of pytest, it will automatically
deactivate itself.

`(4.6.x is the earliest pytest branch that still accepts community bugfixes.)
<https://docs.pytest.org/en/stable/py27-py34-deprecation.html>`__

Hypothesis-based tests should continue to work in earlier versions of
pytest, but enhanced integrations provided by the plugin
(such as ``--hypothesis-show-statistics`` and other command-line flags)
will no longer be available in obsolete pytest versions.
