RELEASE_TYPE: minor

:func:`~hypothesis.strategies.text` now occasionally generates from a preselected list of strings which are likely to find bugs. These include ligatures, right-to-left and top-to-bottom text, emojis, emoji modifiers, strings like ``"Infinity"``, ``"None"``, and ``"FALSE"``, and other terrible things.

This is especially useful when testing the full unicode range, where the search space is too large for uniform sampling to be very effective.

Many thanks to the `Big List of Naughty Strings <https://github.com/minimaxir/big-list-of-naughty-strings>`_, `Text Rendering Hates You <https://faultlore.com/blah/text-hates-you/>`_, and `Text Editing Hates You Too <https://lord.io/text-editing-hates-you-too/>`_ for forming the basis of this list.
