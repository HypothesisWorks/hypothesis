RELEASE_TYPE: patch

This release extends a recent shrinking improvement to values built by
mapping string concatenation, single-field formatting, or ``str()`` itself
over another strategy, such as ``st.text().map("id-{}".format)``,
``st.sampled_from(...).map(lambda s: "id-" + s)``, or
``st.integers().map(str)``.  When such a strategy is the wider branch of a
union, values produced by a more specific branch can now be re-encoded and
shrunk as if the mapped strategy had generated them.
