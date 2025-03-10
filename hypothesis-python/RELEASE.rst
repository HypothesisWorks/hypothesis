RELEASE_TYPE: patch

For strategies which draw make recursive draws, including :func:`~hypothesis.strategies.recursive` and :func:`~hypothesis.strategies.deferred`, we now generate examples with duplicated subtrees more often. This tends to uncover interesting behavior in tests.

For instance, we might now generate a tree like this more often (though the details depend on the strategy):

.. code-block:: none

                 ┌─────┐
          ┌──────┤  a  ├──────┐
          │      └─────┘      │
       ┌──┴──┐             ┌──┴──┐
       │  b  │             │  a  │
       └──┬──┘             └──┬──┘
     ┌────┴────┐         ┌────┴────┐
  ┌──┴──┐   ┌──┴──┐   ┌──┴──┐   ┌──┴──┐
  │  c  │   │  d  │   │  b  │   │ ... │
  └─────┘   └─────┘   └──┬──┘   └─────┘
                    ┌────┴────┐
                 ┌──┴──┐   ┌──┴──┐
                 │  c  │   │  d  │
                 └─────┘   └─────┘
