RELEASE_TYPE: minor

- :func:`~hypothesis.strategies.sampled_from` can now sample from
  one-dimensional numpy ndarrays. Sampling from multi-dimensional
  ndarrays still results in a deprecation warning. Thanks to Charlie
  Tanksley for this patch.
