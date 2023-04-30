RELEASE_TYPE: minor

Sick of adding :obj:`@example() <hypothesis.example>`\ s by hand?
Our Pytest plugin now writes ``.patch`` files to insert them for you, making
`this workflow <https://blog.nelhage.com/post/property-testing-like-afl/>`__
easier than ever before.

Note that you'll need :pypi:`LibCST` (via :ref:`codemods`), and that
:obj:`@example().via() <hypothesis.example.via>` requires :pep:`614`
(Python 3.9 or later).
