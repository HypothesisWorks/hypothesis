RELEASE_TYPE: patch

This patch changes the internal structure of some strategies in the NumPy extra
which were not dependent on NumPy. They are moved to a separate private module
so that in the future Hypothesis can re-use these strategies for other purposes
(i.e. Array API support in :issue:`3065`).
