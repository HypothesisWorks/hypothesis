This adds support for numpy types to `Hypothesis <https://github.com/DRMacIver/hypothesis>`_.

This should be considered more of a prototype than a serious piece of
production software. Usage is as follows:

.. code:: python

    >>> from hypothesis import find
    >>> from hypothesis.extra.numpy import arrays
    >>> find(arrays(float, 2), lambda x: x.sum() >= 1)
    array([ 1.,  0.])
    >>> find(arrays(bool, (2, 2)), lambda x: x.any())
    array([[False, False],
           [ True, False]], dtype=bool)
    >>> find(arrays('uint64', (2, 2)), lambda x: x.any())
    array([[1, 0],
           [0, 0]], dtype=uint64)
