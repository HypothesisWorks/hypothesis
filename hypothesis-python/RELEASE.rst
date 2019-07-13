RELEASE_TYPE: minor


This release implements :func:`~hypothesis.extra.numpy.basic_indices`, generating valid indices for numpy arrays (:issue:`1930`).

It returns a tuple for each dimension, as per ``numpy`` [indexing](https://docs.scipy.org/doc/numpy/reference/arrays.indexing.html) documentation:
    
    In Python, `x[(exp1, exp2, ..., expN)]`` is equivalent to `x[exp1, exp2, ..., expN]`; the latter is just syntactic sugar for the former.

Each  `exprN` can be:
    - an integers, positive or negative, 
    - a slice object, as generated from `st.slices(s)`,
    - an `Ellipsis` object,
    - a `numpy.newaxis`.

`Ellipsis` and `numpy.newaxis` are optional and can be adjusted with the arguments.




