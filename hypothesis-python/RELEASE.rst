RELEASE_TYPE: patch

This patch fixes argument validation on :func:`~hypothesis.strategies.deferred`
such that we raise ``InvalidArgument`` at call time instead of 
at run time if the input to :func:`~hypothesis.strategies.deferred` is not a 
zero-argument function. See :issue:`2272`.