RELEASE_TYPE: patch

This patch improves the type annotations in :mod:`hypothesis.extra.numpy`,
which makes inferred types more precise for both :pypi:`mypy` and
:pypi:`pyright`, and fixes some strict-mode errors on the latter.

Thanks to Jonathan Plasse for reporting and fixing this in :pull:`3889`!
