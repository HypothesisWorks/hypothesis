RELEASE_TYPE: minor

This release adds support for variable-width bytes in our IR layer (:issue:`3921`), which should mean improved performance anywhere you use :func:`~hypothesis.strategies.binary`. If you maintain an alternative backend as part of our (for now explicitly unstable) :ref:`alternative-backends`, this release changes the ``draw_*`` interface and may be a breaking change for you.
