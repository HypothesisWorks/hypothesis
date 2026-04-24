RELEASE_TYPE: minor

The internal :class:`~hypothesis.vendor.pretty.RepresentationPrinter` gains
``deferred()`` and ``finalize()`` methods.  Calling ``deferred()`` returns
a new printer whose output will be spliced into the original at the point
``deferred()`` was called once ``finalize()`` is called on the parent;
this is useful for building up output whose contents are only known
after surrounding output has been written.  Calls on deferred printers
are recorded as concrete primitive operations so the snapshot is
unaffected by later mutation of any pretty-printed objects.
