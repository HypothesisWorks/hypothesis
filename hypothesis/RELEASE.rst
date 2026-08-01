RELEASE_TYPE: minor

:func:`~hypothesis.strategies.characters` now issues the new
:class:`~hypothesis.errors.NonRoundTrippableCharactersWarning` if the
``codec`` argument allows generating characters which encode successfully
but do not decode back to the same character - for example the yen sign
becomes a backslash under ``shift_jis`` - since strings containing them do
not round-trip (:issue:`4813`).  Pass each such character in
``include_characters`` to generate it without the warning, or in
``exclude_characters`` to generate only characters which round-trip.
