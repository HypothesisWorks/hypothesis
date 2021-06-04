RELEASE_TYPE: patch

This patch teaches :doc:`the Ghostwriter <ghostwriter>` how to find
:np-ref:`custom ufuncs <ufuncs.html>` from *any* module that defines them,
and that ``yaml.unsafe_load()`` does not undo ``yaml.safe_load()``.
