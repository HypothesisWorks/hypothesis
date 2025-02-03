RELEASE_TYPE: patch

Fixes a bug since around :ref:`version 6.124.4 <v6.124.4>` where we might have generated ``-0.0`` for ``st.floats(min_value=0.0)``, which is unsound.
