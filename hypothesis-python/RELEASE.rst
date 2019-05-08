RELEASE_TYPE: patch

This patch fixes an OverflowError in
:func:`from_type(xrange) <hypothesis.strategies.from_type>` on Python 2.

It turns out that not only do the ``start`` and ``stop`` values have to
fit in a C long, but so does ``stop - start``.  We now handle this even
on 32bit platforms, but remind users that Python2 will not be supported
after 2019 without specific funding.
