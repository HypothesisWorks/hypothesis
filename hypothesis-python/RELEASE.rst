RELEASE_TYPE: minor

The :doc:`Hypothesis database <database>` now supports a pub-sub interface to efficiently listen for changes in the database, via ``.add_listener`` and ``.remove_listener``. While all databases that ship with Hypothesis support this interface, implementing it is not required for custom database subclasses. Hypothesis will warn when trying to listen on a database without support.

This feature is currently only used downstream in `hypofuzz <https://github.com/zac-hd/hypofuzz>`_.
