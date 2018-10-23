RELEASE_TYPE: patch

Traceback elision is now disabled on Python 2, to avoid an import-time
:class:`python:SyntaxError` under Python < 2.7.9 (Python: :bpo:`21591`,
:ref:`Hypothesis 3.79.2 <v3.79.2>`: :issue:`1648`).

We encourage all users to `upgrade to Python 3 before the end of 2019
<https://pythonclock.org/>`_.
