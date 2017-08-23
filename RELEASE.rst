RELEASE_TYPE: patch

This release fixes some minor bugs in argument validation:

    * `hypothesis.extra.numpy` dtype strategies would raise an internal error
      instead of an InvalidArgument exception when passed an invalid
      endianness specification.
    * ``fractions()`` would raise an internal error instead of an InvalidArgument
      if passed ``float("nan")`` as one of its bounds.
    * The error message for passing ``float("nan")`` as a bound to various
      strategies has been improved.
    * Various bound arguments will now raise ``InvalidArgument`` in cases where
      they would previously have raised an internal ``TypeError`` or
      ``ValueError`` from the relevant conversion function.
    * :func:`~hypothesis.strategies.streaming` would not have emitted a
      deprecation warning when called with an invalid argument.
