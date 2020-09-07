RELEASE_TYPE: patch

This patch fixes a problem with ``st.builds()`` that was not able to
generate valid data for annotated classes with constructors.

Thanks to Nikita Sobolev for fixing :issue:`2603`!
