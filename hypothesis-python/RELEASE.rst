RELEASE_TYPE: patch

Hypothesis generally recommends that the ``.hypothesis`` directory not be checked into version control. As a result, Hypothesis now automatically creates a ``.gitignore`` with ``*`` in the ``.hypothesis`` directory, which excludes it from being tracked by git.

If you do want to check ``.hypothesis`` into git, you can remove the ``.gitignore`` file. Hypothesis will not re-create it unless the entire ``.hypothesis`` directory is removed.
