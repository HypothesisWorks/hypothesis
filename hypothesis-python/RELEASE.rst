RELEASE_TYPE: patch

This patch updates our internal testing for the :ref:`Array API extra
<array-api>` by using entry points (introduced in `#297
<https://github.com/data-apis/array-api/pull/297>`_). In the future this should
allow us to automatically test that our strategies work with multiple Array API
adopters beyond just NumPy. There is no user-visible change.
