RELEASE_TYPE: patch

|st.characters| now validates that the elements of the ``exclude_characters`` and ``include_characters`` arguments are single characters, which was always assumed internally. For example, ``exclude_characters=["a", "b"]`` is valid while ``exclude_characters=["ab"]`` will now raise an error up-front.
