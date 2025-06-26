RELEASE_TYPE: patch

Fixes an error when the ``_pytest`` module is present in ``sys.modules``, but *not* the ``_pytest.outcomes`` or ``_pytest.fixtures`` modules. This can happen with code that imports just ``_pytest``, without importing ``pytest``.
