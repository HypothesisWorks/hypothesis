RELEASE_TYPE: patch

This patch supports assigning ``settings = settings(...)`` as a class attribute
on a subclass of a ``.TestCase`` attribute of a :class:`~hypothesis.stateful.RuleBasedStateMachine`.
Previously, this did nothing at all.

.. code-block: python

    # works as of this release
    class TestMyStatefulMachine(MyStatefulMachine.TestCase):
        settings = settings(max_examples=10000)

    # the old way still works, but it's more verbose.
    MyStateMachine.TestCase.settings = settings(max_examples=10000)
    class TestMyStatefulMachine(MyStatefulMachine.TestCase):
        pass

Thanks to Joey Tran for reporting these settings-related edge cases in stateful testing.
