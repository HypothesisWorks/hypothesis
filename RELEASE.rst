RELEASE_TYPE: patch

Hypothesis no longer propagates the dynamic scope of settings into strategy
definitions.

This release is a small change to something that was never part of the public
API and you will almost certainly not notice any effect unless you're doing
something surprising, but for example the following code will now give a
different answer in some circumstances:

.. code-block:: python

    import hypothesis.strategies as st
    from hypothesis import settings

    CURRENT_SETTINGS = st.builds(lambda: settings.default)

(We don't actually encourage you writing code like this)

Previously this would have generated the settings that were in effect at the
point of definition of ``CURRENT_SETTINGS``. Now it will generate the settings
that are used for the current test.

It is very unlikely to be significant enough to be visible, but you may also
notice a small performance improvement.
