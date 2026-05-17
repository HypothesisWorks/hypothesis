RELEASE_TYPE: patch

Improved performance of resolving recursive abstract classes with
``st.from_type()`` when subclasses include union annotations referencing the
abstract parent.
