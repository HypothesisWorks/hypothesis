RELEASE_TYPE: patch

This patch improves :doc:`observability <observability>` reports by moving
timing information from ``metadata`` to a new ``timing`` key, and supporting
conversion of additional argument types to json rather than string reprs
via a ``.to_json()`` method (including e.g. Pandas dataframes).

Additionally, the :obj:`~hypothesis.HealthCheck.too_slow` health check will
now report *which* strategies were slow, e.g. for strategies a, b, c, ...::

        count | fraction |    slowest draws (seconds)
    a |    3  |     65%  |      --      --      --   0.357,  2.000
    b |    8  |     16%  |   0.100,  0.100,  0.100,  0.111,  0.123
    c |    3  |      8%  |      --      --   0.030,  0.050,  0.200
    (skipped 2 rows of fast draws)
