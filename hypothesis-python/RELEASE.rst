RELEASE_TYPE: patch

This patch causes a [note to be included](https://peps.python.org/pep-0678/) when :func:`~hypothesis.strategies.sampled_from` is given a nonempty collection of all strategy values _and_ the `given`-decorated test fails with a `TypeError` (:issue:`3819``).
This is because such a call is suggestive of intent to instead use :func:`~hypothesis.strategies.one_of`.
