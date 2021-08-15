RELEASE_TYPE: minor

This release emits a more useful error message when :func:`@given() <hypothesis.given>`
is applied to a coroutine function, i.e. one defined using ``async def`` (:issue:`3054`).

This was previously only handled by the generic :obj:`~hypothesis.HealthCheck.return_value`
health check, which doesn't direct you to use either :ref:`a custom executor <custom-function-execution>`
or a library such as :pypi:`pytest-trio` or :pypi:`pytest-asyncio` to handle it for you.
