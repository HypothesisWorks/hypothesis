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

The default storage format is as a fairly opaque directory structure. Each test
corresponds to a directory, and each example to a file within that directory.
The standard location for it is .hypothesis/examples in your current working
directory. You can override this, either by setting either the database\_file property on
a settings object (you probably want to specify it on settings.default) or by setting the
HYPOTHESIS\_DATABASE\_FILE environment variable.

There is also a legacy sqlite3 based format. This is mostly still supported for
compatibility reasons, and support will be dropped in some future version of
Hypothesis. If you use a database file name ending in .db, .sqlite or .sqlite3
that format will be used instead.

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

The only currently supported workflow for this (though it would be easy enough to add new ones)
is via checking the examples directory into version control.

The directory structure is designed so that it is entirely suitable for checking
in to git, mercurial, or any similar version control system. It will be updated
reasonably often, so you might not want to do that in the course of normal
development, but it will correctly handle merges, deletes, etc without a
problem if you just add the directory into version control.

Note: There are other files in .hypothesis but everything other than the examples will be
transparently created on demand. You don't need to and probably shouldn't check those into git.
Adding .hypothesis/eval_source to your .gitignore or equivalent is probably a good idea.
