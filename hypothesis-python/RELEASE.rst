RELEASE_TYPE: patch

This patch improves annotations on some of Hypothesis' internal functions, in order to 
deobfuscate the signatures of some strategies. In particular, strategies shared between 
:ref:`hypothesis.extra.numpy <hypothesis-numpy>` and 
:ref:`the hypothesis.extra.array_api extra <array-api>` will benefit from this patch.
