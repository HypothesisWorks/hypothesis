========
Database
========

When Hypothesis finds a bug it stores enough information in its database to reproduce it. This
enables you to have a classic testing workflow of find a bug, fix a bug, and be confident that
this is actually doing the right thing because Hypothesis will start by retrying the examples that
broke things last time.

-----------
Limitations
-----------

The database is best thought of as a cache that you never need to invalidate: Information may be
lost when you upgrade a Hypothesis version or change your test, so you shouldn't rely on it for
correctness - if there's an example you want to ensure occurs each time then :ref:`there's a feature for
including them in your source code <providing-explicit-examples>` - but it helps the development
workflow considerably by making sure that the examples you've just found are reproduced.

The database also records examples that exercise less-used parts of your
code, so the database may update even when no failing examples were found.

--------------------------------------------
Upgrading Hypothesis and changing your tests
--------------------------------------------

The design of the Hypothesis database is such that you can put arbitrary data in the database
and not get wrong behaviour. When you upgrade Hypothesis, old data *might* be invalidated, but
this should happen transparently. It can never be the case that e.g. changing the strategy
that generates an argument gives you data from the old strategy.

-------------------------------
ExampleDatabase implementations
-------------------------------

Hypothesis' default :obj:`~hypothesis.settings.database` setting creates a
:class:`~hypothesis.database.DirectoryBasedExampleDatabase` in your current working directory,
under ``.hypothesis/examples``.  If this location is unusable, e.g. because you do not have
read or write permissions, Hypothesis will emit a warning and fall back to an
:class:`~hypothesis.database.InMemoryExampleDatabase`.

Hypothesis provides the following :class:`~hypothesis.database.ExampleDatabase` implementations:

.. autoclass:: hypothesis.database.InMemoryExampleDatabase
.. autoclass:: hypothesis.database.DirectoryBasedExampleDatabase
.. autoclass:: hypothesis.database.GitHubArtifactDatabase
.. autoclass:: hypothesis.database.ReadOnlyDatabase
.. autoclass:: hypothesis.database.MultiplexedDatabase
.. autoclass:: hypothesis.database.BackgroundWriteDatabase
.. autoclass:: hypothesis.extra.redis.RedisExampleDatabase

---------------------------------
Defining your own ExampleDatabase
---------------------------------

You can define your :class:`~hypothesis.database.ExampleDatabase`, for example
to use a shared datastore, with just a few methods:

.. autoclass:: hypothesis.database.ExampleDatabase
   :members:
