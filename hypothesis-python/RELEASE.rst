RELEASE_TYPE: minor

:ref:`statistics` now include the best score seen for each label, which can help avoid
`the threshold problem <https://hypothesis.works/articles/threshold-problem/>`__  when
the minimal example shrinks right down to the threshold of failure (:issue:`2180`).
