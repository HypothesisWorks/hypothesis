RELEASE_TYPE: minor

Enable :doc:`Ghostwritten <ghostwriter>` to accept a :func:`~python.__builtins__.classmethod` or :func:`~python.__builtins__.staticmethod` as input.
:func:`~hypothesis.extra.ghostwriter.magic` can discover :func:`~python.__builtins__.classmethod` or :func:`~python.__builtins__.staticmethod` of classes through accepting a module or a class as input.
These changes are also enable in the command line interface.
(:issue:`3318`).
