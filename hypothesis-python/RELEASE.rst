RELEASE_TYPE: minor

This release adds an optional ``payload`` argument to :func:`hypothesis.event`,
so that you can clearly express the difference between the label and the value
of an observation.  :ref:`statistics` will still summarize it as a string, but
future observability options can preserve the distinction.
