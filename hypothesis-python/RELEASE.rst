RELEASE_TYPE: patch

This patch makes the :obj:`~hypothesis.HealthCheck.too_slow` health check more
consistent with long :obj:`~hypothesis.settings.deadline` tests (:issue:`3367`)
and fixes an install issue under :pypi:`pipenv` which was introduced in
:ref:`Hypothesis 6.47.2 <v6.47.2>` (:issue:`3374`).
