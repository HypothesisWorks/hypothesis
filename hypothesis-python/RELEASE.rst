RELEASE_TYPE: patch

This release fixes two very minor bugs in the core engine:

* it fixes a corner case that was missing in :ref:`3.66.28 <v3.66.28>`, which
  should cause shrinking to work slightly better.
* it fixes some logic for how shrinking interacts with the database that was
  causing Hypothesis to be insufficiently aggressive about clearing out old
  keys.
