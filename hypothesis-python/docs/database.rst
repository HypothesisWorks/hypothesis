===============================
The Hypothesis Example Database
===============================

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

--------------
File locations
--------------

The default storage format is as a fairly opaque directory structure. Each test
corresponds to a directory, and each example to a file within that directory.
The standard location for it is ``.hypothesis/examples`` in your current working
directory. You can override this by setting the
:obj:`~hypothesis.settings.database` setting.

If you have not configured a database and the default location is unusable
(e.g. because you do not have read/write permission), Hypothesis will issue
a warning and then fall back to an in-memory database.

--------------------------------------------
Upgrading Hypothesis and changing your tests
--------------------------------------------

The design of the Hypothesis database is such that you can put arbitrary data in the database
and not get wrong behaviour. When you upgrade Hypothesis, old data *might* be invalidated, but
this should happen transparently. It can never be the case that e.g. changing the strategy
that generates an argument gives you data from the old strategy.

-----------------------------
Sharing your example database
-----------------------------

.. note::
    If specific examples are important for correctness you should use the
    :func:`@example <hypothesis.example>` decorator, as the example database may discard entries due to
    changes in your code or dependencies.  For most users, we therefore
    recommend using the example database locally and possibly persisting it
    between CI builds, but not tracking it under version control.

The examples database can be shared simply by checking the directory into
version control, for example with the following ``.gitignore``::

    # Ignore files cached by Hypothesis...
    .hypothesis/*
    # except for the examples directory
    !.hypothesis/examples/

Like everything under ``.hypothesis/``, the examples directory will be
transparently created on demand.  Unlike the other subdirectories,
``examples/`` is designed to handle merges, deletes, etc if you just add the
directory into git, mercurial, or any similar version control system.
