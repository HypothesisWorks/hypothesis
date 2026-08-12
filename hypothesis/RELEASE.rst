RELEASE_TYPE: patch

This release improves our heuristic for when to run the |Phase.target| phase,
which optimises scores from :func:`hypothesis.target`. Behaviour is unchanged
for :obj:`~hypothesis.settings.max_examples` below 1000. For larger budgets
we now start optimising much earlier, and alternate between generation and
optimisation for as long as scores keep improving, instead of running a
single optimisation pass halfway through the run. Exploratory searches using
:func:`~hypothesis.target` with a large budget should now make much better
use of it (:issue:`3176`).
