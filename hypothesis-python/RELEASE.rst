RELEASE_TYPE: minor

This release upgrades the :ref:`explain phase <phases>` (:issue:`3411`).

* Following the first failure, Hypothesis will (:ref:`usually <phases>`) track which
  lines of code were executed by passing and failing examples, and report where they
  diverged - with some heuristics to drop unhelpful reports.  This is an existing
  feature, now upgraded and newly enabled by default.

* After shrinking to a minimal failing example, Hypothesis will try to find parts of
  the example -- e.g. separate args to :func:`@given() <hypothesis.given>` -- which
  can vary freely without changing the result of that minimal failing example.
  If the automated experiments run without finding a passing variation, we leave a
  comment in the final report:

  .. code-block:: python

      test_x_divided_by_y(
          x=0,  # or any other generated value
          y=0,
      )

Just remember that the *lack* of an explanation sometimes just means that Hypothesis
couldn't efficiently find one, not that no explanation (or simpler failing example)
exists.
