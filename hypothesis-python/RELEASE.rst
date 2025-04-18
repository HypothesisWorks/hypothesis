RELEASE_TYPE: patch

Improves several issues from code introduced in :ref:`version 6.131.1 <v6.131.1>`:

* Improve speed of constants collection, and add a hard internal time limit to aviod running for too long.
* Fix a ``RecursionError`` on deeply nested code.
