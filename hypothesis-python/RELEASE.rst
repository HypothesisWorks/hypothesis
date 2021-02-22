RELEASE_TYPE: minor

This release adds :ref:`the explain phase <phases>`, in which Hypothesis
attempts to explain *why* your test failed by pointing to suspicious lines
of code (i.e. those which were always, and only, run on failing inputs).
We plan to include "generalising" failing examples in this phase in a
future release (:issue:`2192`).
