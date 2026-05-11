RELEASE_TYPE: patch

This release substantially improves our internal distribution for generating integers. This release has the most visible effect on |st.integers|, but may incidentally improve other strategies which draw integers internally.

Our integers distribution had two problems. First, it had jagged discontinuities at certain values where we switched sampling approaches. Second, it used a different distribution for bounded and unbounded ranges, which resulted in ``st.integers()`` and ``st.integers(-2**64, 2**64)`` producing very different distributions despite being semantically similar.

We now use a smooth distribution for both ``st.integers()`` and ``st.integers(a, b)``, which fixes both of these issues. This should substantially improve our testing power in certain cases.

The only way this release should be user-visible is that it finds more bugs! If this release is user-visible in other ways - for example, because it is slower, or produces a worse distribution in some cases - please open an issue.
