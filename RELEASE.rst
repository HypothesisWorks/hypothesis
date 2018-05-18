RELEASE_TYPE: minor

This release add ``initialize`` decorator for stateful testing
(originally discussed in :issue:`1216`). ``initialize`` act as a special rule
that is only called once at the very beginning of each run of the state-machine.
