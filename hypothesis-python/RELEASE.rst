RELEASE_TYPE: patch

This patch teaches :command:`hypothesis write` to default to ghostwriting
tests with ``--style=pytest`` only if :pypi:`pytest` is installed, or
``--style=unittest`` otherwise.
