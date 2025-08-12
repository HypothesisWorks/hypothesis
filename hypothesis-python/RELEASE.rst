RELEASE_TYPE: minor

On Python 3.14, |memoryview| is newly generic. This release adds the ability for |st.from_type| to resolve generic |memoryview| types on 3.14, like ``st.from_type(memoryview[CustomBufferClass])`` . ``CustomBufferClass`` must implement ``__buffer__``, as expected by |memoryview|.
