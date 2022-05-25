RELEASE_TYPE: minor

Enable :module:`hypothesis.extra.ghostwriter` to accept a py:decorator::`@classmethod` or py:decorator::`@staticmethod` as input.
:module:`hypothesis.extra.ghostwriter.magic` can discover py:decorator::`@classmethod` or py:decorator::`@staticmethod` of classes through accepting a module or a class as input.
These changes are also enable in the command line interface.
(:issue:`3318`).
