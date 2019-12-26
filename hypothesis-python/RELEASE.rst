RELEASE_TYPE: minor

This release improves support for the SupportsOp protocols from the :mod:`python:typing` 
module when using on :func:`~hypothesis.strategies.from_type` as outlined in :issue:`2292`.
The following types now generate more wide ranging and correct strategies when called 
with :func:`~hypothesis.strategies.from_type`:

- :class:`python:typing.SupportsAbs`
- :class:`python:typing.SupportsBytes`
- :class:`python:typing.SupportsComplex`
- :class:`python:typing.SupportsInt`
- :class:`python:typing.SupportsFloat`
- :class:`python:typing.SupportsRound`
  
Note that using :func:`~hypothesis.strategies.from_type` with one of the above strategies will not
ensure that the the specified function will execute successfully (ie : the strategy returned for
``from_type(typing.SupportsAbs)`` may include NaNs or things this will cause the :func:`python:abs`
function to error. )

Thanks to Lea Provenzano for this patch.