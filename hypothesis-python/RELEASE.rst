RELEASE_TYPE: patch

This release improves integer shrinking by folding the endpoint upweighting for :func:`~hypothesis.strategies.integers` into the ``weights`` parameter of our IR (:issue:`3921`).

If you maintain an alternative backend as part of our (for now explicitly unstable) :ref:`alternative-backends`, this release changes the type of the ``weights`` parameter to ``draw_integer`` and may be a breaking change for you.
