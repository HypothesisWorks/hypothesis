RELEASE_TYPE: patch

Fixes a race condition in |ExampleDatabase.add_listener| for |DirectoryBasedExampleDatabase| after version :ref:`6.135.1 <v6.135.1>` where the listener might have tried to read a file that doesn't exist.
