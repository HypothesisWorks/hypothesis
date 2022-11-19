RELEASE_TYPE: minor

This release increases Hypothesis' minimum supported version of NumPy to 1.19.0.

This release adds the strategy :func:`~hypothesis.extra.numpy.rand_generators`, which 
draws instances of :obj:`numpy.random.Generator <numpy:numpy.random.Generator>` backed 
by a bit-generator initialized with a Hypothesis-controlled seed. Fail cases display 
the initial seed that was used to create the generator, enabling reproducibility.
Accordingly, Hypothesis can now infer a strategy for the ``numpy.random.Generator`` 
type.
