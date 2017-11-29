RELEASE_TYPE: minor

This release improves how various ways of seeding Hypothesis interact with the
example database:

* Using the example database with :func:`~hypothesis.seed` is now deprecated.
  You should set ``database=None`` if you are doing that. This will only warn
  if you actually load examples from the database while using ``@seed``.
* The :attr:`~hypothesis.settings.derandomize` will behave the same way as
  ``@seed``.
* Using ``--hypothesis-seed`` will disable use of the database.
* If a test used examples from the database, it will not suggest using a seed
  to reproduce it, because that won't work.

This work was funded by `Smarkets <https://smarkets.com/>`_.
