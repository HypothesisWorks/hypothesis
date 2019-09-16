RELEASE_TYPE: patch

This patch fixes a bug in the :pypi:`attrs` search strategy that made Hypothesis fail to infer types from the :mod:`typing` module such as `Union[int, str]`, `Dict[str,int]` or `List[int]` (:issue:`2091`).

Hypothesis will now use :func:`~hypothesis.strategies.from_type` when encountering a generic type in an `attrs` attribute.
