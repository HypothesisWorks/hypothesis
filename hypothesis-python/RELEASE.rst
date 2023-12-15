RELEASE_TYPE: patch

This patch fixes a bug introduced in :ref:`version 6.92.0 <v6.92.0>`, where using :func:`~python:dataclasses.dataclass` with a :class:`~python:collections.defaultdict` field as a strategy argument would error.
