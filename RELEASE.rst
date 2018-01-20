RELEASE_TYPE: patch

This is a small refactoring release that changes how Hypothesis detects when
the structure of data generation depends on earlier values generated (e.g. when
using :ref:`flatmap <flatmap>` or :func:`~hypothesis.strategies.composite`).
It should not have any observable effect on behaviour.
