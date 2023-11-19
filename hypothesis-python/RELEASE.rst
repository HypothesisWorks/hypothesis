RELEASE_TYPE: minor

This release makes it an error to assign ``settings = settings(...)``
as a class attribute on a :class:`~hypothesis.stateful.RuleBasedStateMachine`.
This has never had any effect, and it should be used as a decorator instead:

.. code-block: python

    class BadMachine(RuleBasedStateMachine):
        """This doesn't do anything, and is now an error!"""
        settings = settings(derandomize=True)

    @settings(derandomize=True)
    class GoodMachine(RuleBasedStateMachine):
        """This is the right way to do it :-)"""
