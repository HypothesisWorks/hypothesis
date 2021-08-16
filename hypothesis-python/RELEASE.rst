RELEASE_TYPE: patch

This patch ensures that registering a strategy for a subclass of a a parametrised
generic type such as ``class Lines(Sequence[str]):`` will not "leak" into unrelated
strategies such as ``st.from_type(Sequence[int])`` (:issue:`2951`).
Unfortunately this fix requires :pep:`560`, meaning Python 3.7 or later.
