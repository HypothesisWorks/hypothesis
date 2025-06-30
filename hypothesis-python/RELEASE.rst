RELEASE_TYPE: patch

Remove an internal assertion which could trigger if (1) a lambda was present in the source code of a test, (2) and the source code file was edited on disk between the start of the python process and when Hypothesis runs the property.
