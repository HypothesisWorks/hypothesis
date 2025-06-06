RELEASE_TYPE: patch

This release adds the experimental and unstable |OBSERVABILITY_CHOICES| option for :ref:`observability <observability>`. If set, the choice sequence is included in ``metadata.choice_nodes``, and choice sequence spans are included in ``metadata.choice_spans``.

These are relatively low-level implementation detail of Hypothesis, and are exposed in observability for users building tools or research on top of Hypothesis. See |PrimitiveProvider| for more details about the choice sequence and choice spans.

We are actively working towards a better interface for this. Feel free to use |OBSERVABILITY_CHOICES| to experiment, but don't rely on it yet!
