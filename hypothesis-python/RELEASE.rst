RELEASE_TYPE: patch

This patch fixes a deprecation warning if you're using recent versions
of :pypi:`importlib-metadata` (:issue:`2934`), which we use to load
:ref:`third-party plugins <entry-points>` such as `Pydantic's integration
<https://pydantic-docs.helpmanual.io/hypothesis_plugin/>`__.
On older versions of :pypi:`importlib-metadata`, there is no change and
you don't need to upgrade.
