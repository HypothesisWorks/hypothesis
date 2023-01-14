RELEASE_TYPE: patch

This patch tweaks :func:`xps.arrays` internals to improve PyTorch compatibility.
Specifically, ``torch.full()`` does not accept integers as the shape argument
(n.b. technically "size" in torch), but such behaviour is expected in internal
code, so we copy the ``torch`` module and patch in a working ``full()`` function.
