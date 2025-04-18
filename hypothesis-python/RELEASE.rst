RELEASE_TYPE: patch

Improves several issues surrounding the code introduced in :ref:`version 6.131.1 <v6.131.1>`:

* Improve speed of constants collection.
* Cache constants to the ``.hypothesis`` directory for future runs.
* Fix a ``RecursionError`` on parsing deeply nested code.
