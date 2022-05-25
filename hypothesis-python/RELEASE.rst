RELEASE_TYPE: minor

Enable :doc:`Ghostwritten <ghostwriter>` to accept a :decorator:`~python.__builtin__.classmethod` or :decorator:`~python.__builtin__.staticmethod` as input.
:module:`~hypothesis.extra.ghostwriter.magic` can discover :decorator:`~python.__builtin__.classmethod` or :decorator:`~python.__builtin__.staticmethod` of classes through accepting a module or a class as input.
These changes are also enable in the command line interface.
(:issue:`3318`).
