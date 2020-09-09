RELEASE_TYPE: patch

This patch adds explicit :class:`~python:typing.Optional` annotations to our public API,
to better support users who run :pypi:`mypy` with ``--strict`` or ``no_implicit_optional=True``.

Thanks to Krzysztof Przybyła for bringing this to our attention and writing the patch!
