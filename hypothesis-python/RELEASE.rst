RELEASE_TYPE: patch

This patch improves the :func:`~hypothesis.strategies.tuples` strategy
type annotations, to preserve the element types for up to length-five
tuples (:issue:`3005`).

As for :func:`~hypothesis.strategies.one_of`, this is the best we can do
before a `planned extension <https://mail.python.org/archives/list/typing-sig@python.org/thread/LOQFV3IIWGFDB7F5BDX746EZJG4VVBI3/>`__
to :pep:`646` is released, hopefully in Python 3.11.
