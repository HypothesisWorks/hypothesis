RELEASE_TYPE: patch

This patch fixes our |st.from_regex| type annotations so that ``from_regex(..., alphabet=None)`` is accepted.

This patch also adds unicode line breaks and thai combining vowels to our list of constant strings to upweight at runtime.
