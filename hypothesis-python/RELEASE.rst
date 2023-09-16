RELEASE_TYPE: minor

This release deprecates the old whitelist/blacklist arguments
to :func:`~hypothesis.strategies.characters`, in favor of
include/exclude arguments which more clearly describe their
effects on the set of characters which can be generated.
