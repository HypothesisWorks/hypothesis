RELEASE_TYPE: patch

This patch makes some quality-of-life improvements to the
:doc:`Ghostwriter <ghostwriter>`: we guess the :func:`~hypothesis.strategies.text`
strategy for arguments named ``text`` (...obvious in hindsight, eh?);
and improved the error message if you accidentally left in a
:func:`~hypothesis.strategies.nothing` or broke your :pypi:`rich` install.
