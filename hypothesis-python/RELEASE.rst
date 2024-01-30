RELEASE_TYPE: patch

This patch slightly changes how we replay examples from
:doc:`the database <database>`: if the behavior of the saved example has
changed, we now keep running the test case instead of aborting at the size
of the saved example.  While we know it's not the *same* example, we might
as well continue running the test!

Because we now finish running a few more examples for affected tests, this
might be a slight slowdown - but correspondingly more likely to find a bug.

We've also applied similar tricks to the :ref:`target phase <phases>`, where
they are a pure performance improvement for affected tests.
