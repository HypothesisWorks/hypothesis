RELEASE_TYPE: patch

This patch implements filter-rewriting for :func:`~hypothesis.strategies.times`
and :func:`~hypothesis.strategies.datetimes`: simple comparison filters such as
``.filter(partial(operator.ge, bound))`` are rewritten into efficient bounds,
as :func:`~hypothesis.strategies.dates` already did.  This includes strategies
inferred from :pypi:`annotated-types` bounds like ``Annotated[datetime, Gt(...)]``,
and contradictory filters now give an empty strategy instead of failing
health checks.
