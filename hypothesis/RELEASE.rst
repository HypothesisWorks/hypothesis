RELEASE_TYPE: minor

:class:`~hypothesis.stateful.Bundle` now supports efficient |.filter|
and |.map| methods, which compose with
:func:`~hypothesis.stateful.consumes` in either order (:issue:`3944`).
Previously, ``consumes(bundle).filter(fn)`` could remove rejected values from
the bundle while retrying, and ``consumes(bundle.filter(fn))`` was a type
error; filtered draws now select among currently-matching values and consume
only the value which was actually drawn.

Thanks to Reagan Lee for the initial implementation of this feature in
:pull:`4084`!
