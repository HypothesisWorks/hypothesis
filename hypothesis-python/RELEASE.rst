RELEASE_TYPE: minor

This release adds the :func:`hypothesis.target` function, which implements
**experimental** support for :ref:`targeted property-based testing <targeted-search>`
(:issue:`1779`).

By calling :func:`~hypothesis.target` in your test function, Hypothesis can
do a hill-climbing search for bugs.  If you can calculate a suitable metric
such as the load factor or length of a queue, this can help you find bugs with
inputs that are highly improbably from unguided generation - however good our
heuristics, example diversity, and deduplication logic might be.  After all,
those features are at work in targeted PBT too!
