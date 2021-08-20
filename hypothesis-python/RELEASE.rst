RELEASE_TYPE: patch

This patch fixes a regression in Hypothesis 6.14.8, where :func:`~hypothesis.strategies.from_type`
failed to resolve types which inherit from multiple parametrised generic types,
affecting the :pypi:`returns` package (:issue:`3060`).
