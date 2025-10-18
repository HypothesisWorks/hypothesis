RELEASE_TYPE: minor

The extras for |hypothesis-numpy| and |hypothesis-pandas| now support automatically inferring a strategy for ``dtype="O"``. Previously, Hypothesis required an explicit elements strategy to be passed, for example ``nps.arrays("O", shape=(1,), elements=st.just(object()))``. Now, Hypothesis automatically infers ``elements=st.from_type(object)``.

Thanks to Shaun Read for identifying and fixing this!
