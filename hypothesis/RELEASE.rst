RELEASE_TYPE: patch

This patch reduces Hypothesis' overhead for each test case. For simple
properties and strategies, generating test cases takes up to a third less time
and shrinking failing examples is up to twice as fast; most tests will see a
smaller improvement. ``import hypothesis`` is also about 20% faster.

This patch also improves import-detection in :ref:`the Ghostwriter <ghostwriter>`
(:issue:`4943`). Ghostwritten tests now import the :func:`functools.partial`
filters that :pypi:`annotated-types` bounds give, including those of a
:func:`~hypothesis.strategies.floats` strategy whose bounds absorb the filter,
and write the metadata of an :obj:`~typing.Annotated` parameter with its module.

Thanks to Zac Kienzle for this fix!
