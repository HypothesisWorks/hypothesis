RELEASE_TYPE: patch

This patch makes Hypothesis compatible with the Python 3.8 alpha, which
changed the representation of code objects to support positional-only
arguments.  Note however that Hypothesis does not (yet) support such
functions as e.g. arguments to :func:`~hypothesis.strategies.builds`
or inputs to :func:`@given <hypothesis.given>`.

Thanks to Paul Ganssle for identifying and fixing this bug.
