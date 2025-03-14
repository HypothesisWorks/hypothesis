Stateful tests
==============

.. autoclass:: hypothesis.stateful.RuleBasedStateMachine

Rules
-----

.. autofunction:: hypothesis.stateful.rule

.. autofunction:: hypothesis.stateful.consumes

.. autofunction:: hypothesis.stateful.multiple

.. autoclass:: hypothesis.stateful.Bundle

.. autofunction:: hypothesis.stateful.initialize

.. autofunction:: hypothesis.stateful.precondition

.. autofunction:: hypothesis.stateful.invariant

Running state machines
----------------------

.. autofunction:: hypothesis.stateful.run_state_machine_as_test

If you want to bypass the TestCase infrastructure you can invoke these manually. The stateful module exposes the function ``run_state_machine_as_test``, which takes an arbitrary function returning a RuleBasedStateMachine and an optional settings parameter and does the same as the class based runTest provided.

This is not recommended as it bypasses some important internal functions, including reporting of statistics such as runtimes and :func:`~hypothesis.event` calls.  It was originally added to support custom ``__init__`` methods, but you can now use :func:`~hypothesis.stateful.initialize` rules instead.
