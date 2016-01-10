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

--------------
File locations
--------------

The default (and currently only) storage format is as rather weirdly unidiomatic JSON saved
in an sqlite3 database. The standard location for that is .hypothesis/examples.db in your current
working directory. You can override this, either by setting either the database\_file property on
a settings object (you probably want to specify it on settings.default) or by setting the
HYPOTHESIS\_DATABASE\_FILE environment variable.

Note: There are other files in .hypothesis but everything other than the examples.db will be
transparently created on demand. You don't need to and probably shouldn't check those into git.
Adding .hypothesis/eval_source to your .gitignore or equivalent is probably a good idea.

--------------------------------------------
Upgrading Hypothesis and changing your tests
--------------------------------------------

The design of the Hypothesis database is such that you can put arbitrary data in the database
and not get wrong behaviour. When you upgrade Hypothesis, old data *might* be invalidated, but
this should happen transparently. It should never be the case that e.g. changing the strategy
that generates an argument sometimes gives you data from the old strategy.

-----------------------------
Sharing your example database
-----------------------------

It may be convenient to share an example database between multiple machines - e.g. having a CI
server continually running to look for bugs, then sharing any changes it makes.

The only currently supported workflow for this (though it would be easy enough to add new ones)
is via checking the examples.db file into git. Hypothesis provides a git merge script, executable
as python -m hypothesis.tools.mergedbs.

For example, in order to make this work with the standard location:

In .gitattributes add:

.. code::

  .hypothesis/examples.db merge=hypothesisdb

And in .git/config add:

.. code::

  [merge "hypothesisdb"]
      name = Hypothesis database files
      driver = python -m hypothesis.tools.mergedbs %O %A %B

This will cause the Hypothesis merge script to be used when both sides of a merge have changed
the example database.
