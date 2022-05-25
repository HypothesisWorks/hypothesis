RELEASE_TYPE: minor

Enable :doc:`Ghostwritten <ghostwriter>` to accept a :func:`~python.__builtin__.classmethod` or :func:`~python.__builtin__.staticmethod` as input.
:func:`~hypothesis.extra.ghostwriter.magic` can discover :func:`~python.__builtin__.classmethod` or :func:`~python.__builtin__.staticmethod` of classes through accepting a module or a class as input.
These changes are also enable in the command line interface.
(:issue:`3318`).
