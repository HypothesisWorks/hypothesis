RELEASE_TYPE: minor

This release adds a leading ``_`` to the name of most internal modules
and packages, as recommended by :pep:`8#public-and-internal-interfaces`
to improve support for introspection and integration with tools such as
`Sphinx autodoc <http://www.sphinx-doc.org/en/stable/ext/autodoc.html>`_
and :pypi:`flake8-docstrings`.

.. note::
    While the *presence* of a leading underscore in some name or containing
    namespace always indicates that the interface is internal, the *absence*
    of an underscore does not indicate that the interface is public.

We are aware that this change will break downstream code that accidentally
depends on our internals, but justified by reducing the chance of future
problems and improving our use of various linting and documentation tools.
(If you *deliberately* depend on our internals, please open an issue
explaining your use-case and we'll see what we can do.)
