RELEASE_TYPE: minor

This release improves the :func:`~hypothesis.extra.numpy.array_shapes`
strategy, to choose an appropriate ``max_side`` argument based on the
``min_side``, and ``max_dims`` based on the ``min_dims``.  An explicit 
error is raised for dimensions greater than 32, which are not supported
by Numpy, as for other invalid combinations of arguments.

Thanks to Jenny Rouleau for writing this feature at the 
`PyCon 2019 Mentored Sprints <https://us.pycon.org/2019/hatchery/mentoredsprints/>`_.
