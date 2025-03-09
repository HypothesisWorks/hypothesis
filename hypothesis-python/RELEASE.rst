RELEASE_TYPE: minor

:func:`~hypothesis.strategies.text` now occasionally generates from a preselected list of strings which are likely to find bugs. These include ligatures, right-to-left and top-to-bottom text, emojis, emoji modifiers, strings like ``"Infinity"``, ``"None"``, and ``"FALSE"``, and other interesting things. This is especially useful when testing the full unicode range, where the search space is too large for uniform sampling to be very effective.

Of course, examples generated this way shrink just like they normally would. It was always possible for Hypothesis to generate these strings; it is just more likely after this change. From the outside, it is as if Hypothesis generated the example completely randomly.

Many thanks to the `Big List of Naughty Strings <https://github.com/minimaxir/big-list-of-naughty-strings>`_, `Text Rendering Hates You <https://faultlore.com/blah/text-hates-you/>`_, and `Text Editing Hates You Too <https://lord.io/text-editing-hates-you-too/>`_ for forming the basis of this list.
