RELEASE_TYPE: patch

This patch reverts :ref:`version 5.2 <v5.2.0>`, due to a
`strange issue <https://github.com/numpy/numpy/issues/15363>`__
where indexing an array of strings can raise an error instead of
returning an item which contains certain surrogate characters.
