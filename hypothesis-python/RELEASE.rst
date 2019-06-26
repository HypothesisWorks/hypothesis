RELEASE_TYPE: patch

This patch makes :func:`~hypothesis.strategies.datetimes` more efficient,
as it now handles short months correctly by construction instead of filtering.
