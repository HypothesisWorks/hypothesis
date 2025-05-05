RELEASE_TYPE: patch

Improve type hints for the single-argument form of |st.one_of|. ``st.one_of(strategies)`` now matches the type of ``st.one_of(*strategies)``. For instance, ``st.one_of([st.integers(), st.none()])`` now has the correct type of ``SearchStrategy[int | None]`` instead of ``SearchStrategy[Any]``.
