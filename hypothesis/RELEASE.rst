RELEASE_TYPE: patch

This patch fixes an internal error when the shrinker tried certain invalid values, for example when shrinking |st.one_of| between text strategies with different alphabets (:issue:4905).
