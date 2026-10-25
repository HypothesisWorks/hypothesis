RELEASE_TYPE: patch

This patch fixes an internal error from |st.lists| with ``unique=True``, when
the elements are a filtered |st.sampled_from| with too few allowed values to
reach ``min_size``.  It also ensures that |st.domains| always generates at
least one subdomain, even with a small ``max_length``.

We also fixed some internal bookkeeping that could go wrong when an exception
was raised and caught during generation, for example by |st.recursive|, which
could make shrinking less effective.

This patch also improves import-detection in :ref:`the Ghostwriter <ghostwriter>`
(:issue:`4943`). Ghostwritten tests now import the :func:`functools.partial`
filters that :pypi:`annotated-types` bounds give, including those of a
:func:`~hypothesis.strategies.floats` strategy whose bounds absorb the filter,
and write the metadata of an :obj:`~typing.Annotated` parameter with its module.

Thanks to Zac Kienzle for this fix!
