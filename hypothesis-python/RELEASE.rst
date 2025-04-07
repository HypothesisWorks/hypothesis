RELEASE_TYPE: patch

This patch deprecates creating a database using the abstract ``ExampleDatabase()`` class. Use one of the following instead:

* Replace ``ExampleDatabase(":memory:")`` with |InMemoryExampleDatabase|.
* Replace ``ExampleDatabase("/path/to/dir")`` with |DirectoryBasedExampleDatabase|.
* Replace ``ExampleDatabase()`` with either |InMemoryExampleDatabase| or |DirectoryBasedExampleDatabase|, depending on your needs. Previously, Hypothesis interpreted ``ExampleDatabase()`` as a |DirectoryBasedExampleDatabase| in the default ``.hypothesis`` directory, with a fallback to |InMemoryExampleDatabase| if that location was not available.
