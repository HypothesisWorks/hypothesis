This release provides a major overhaul to the internals of how Hypothesis
handles shrinking.

This should mostly be visible in terms of getting better examples for tests
which make heavy use of :func:`~hypothesis.strategies.composite`,
:ref`data <interactive-draw>` or :ref`flatmap <flatmap>` where the data
drawn depends a lot on previous choices, especially where size parameters are
affected. Previously Hypothesis would have struggled to reliably produce
good examples here. Now it should do much better. Performance should also be
better for examples with a non-zero ``min_size``.

You may see slight changes to example generation (e.g. improved example
diversity) as a result of related changes to internals, but they are unlikely
to be significant enough to notice.
