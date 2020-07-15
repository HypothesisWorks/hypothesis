RELEASE_TYPE: patch

This patch removes an internal use of ``distutils`` in order to avoid
`this setuptools warning <https://github.com/pypa/setuptools/issues/2261>`__
for some users.
