RELEASE_TYPE: patch

|st.one_of| now chooses a subset of its strategies to disable each time it generates a value. For example, it was previously unlikely that ``st.lists(st.integers() | st.floats() | st.text()`` would generate a long list containing only string values. This is now more likely, along with other uncommon combinations.

This technique is called `swarm testing <https://users.cs.utah.edu/~regehr/papers/swarm12.pdf>`__, and can considerably improve bug-finding power, for instance because some features actively prevent other interesting behavior from running. See :issue:`2643` for more details.
