RELEASE_TYPE: minor

Enable :doc:`Ghostwritten <ghostwriter>` to accept a :obj:`@classmethod <python.__builtins__.classmethod>` or :obj:`@staticmethod <python.__builtins__.staticmethod>` as input.
:func:`~hypothesis.extra.ghostwriter.magic` can discover :obj:`@classmethod <python.__builtins__.classmethod>` or :obj:`@staticmethod <python.__builtins__.staticmethod>` of classes through accepting a module or a class as input.
These changes are also enable in the command line interface.
(:issue:`3318`).
