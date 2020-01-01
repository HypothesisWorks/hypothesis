RELEASE_TYPE: patch

This patch contains mostly-automated refactorings to remove code
that we only needed to support Python 2.  Since Hypothesis is now
Python 3 only (hurray!), there is no user-visible change.

Our sincere thanks to the authors of :pypi:`autoflake`, :pypi:`black`,
:pypi:`isort`, and :pypi:`pyupgrade`, who have each and collectively
made this kind of update enormously easier.
