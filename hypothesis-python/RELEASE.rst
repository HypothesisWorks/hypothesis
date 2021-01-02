RELEASE_TYPE: patch

This patch makes some strategies for collections with a uniqueness constraint
much more efficient, including ``dictionaries(keys=sampled_from(...), values=..)``
and ``lists(tuples(sampled_from(...), ...), unique_by=lambda x: x[0])``.
(related to :issue:`2036`)
