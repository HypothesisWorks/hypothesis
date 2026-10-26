RELEASE_TYPE: patch

This patch makes writing :ref:`observability <observability>` data to
``.hypothesis/observed`` cheaper when tests run in multiple threads, and
defers cleaning up old observation files from import time until
observations are first written.

This patch also improves import-detection in :ref:`the Ghostwriter <ghostwriter>`
(:issue:`4943`). Ghostwritten tests now import the :func:`functools.partial`
filters that :pypi:`annotated-types` bounds give, including those of a
:func:`~hypothesis.strategies.floats` strategy whose bounds absorb the filter,
and write the metadata of an :obj:`~typing.Annotated` parameter with its module.

Thanks to Zac Kienzle for this fix!
