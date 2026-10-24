RELEASE_TYPE: patch

This patch improves import-detection in :doc:`the Ghostwriter <ghostwriter>`
(:issue:`4943`). Ghostwritten tests now import the :func:`functools.partial`
filters that :pypi:`annotated-types` bounds give, including those of a
:func:`~hypothesis.strategies.floats` strategy whose bounds absorb the filter,
and write the metadata of an :obj:`~typing.Annotated` parameter with its module.

Thanks to Zac Kienzle for this fix!
