RELEASE_TYPE: patch

This patch fixes one possible cause of :issue:`966`.  When running
Python 2 with hash randomisation, passing a :obj:`python:bytes` object
to :func:`python:random.seed` would use ``version=1``, which broke
:obj:`~hypothesis.settings.derandomize` (because the seed depended on
a randomised hash).  If :obj:`~hypothesis.settings.derandomize` is
*still* nondeterministic for you, please open an issue.
