=====================================
The Hypothesis Documentation Handbook
=====================================

Good documentation can make the difference between good code and useful code -
and Hypothesis is written to be used, as widely as possible.

This is a working document-in-progress with some tips for how we try to write
our docs, with a little of the what and a bigger chunk of the how.
If you have ideas about how to improve these suggests, meta issues or pull
requests are just as welcome as for docs or code :D

----------------------------
What docs should be written?
----------------------------

All public APIs should be comprehensively described.  If the docs are
confusing to new users, incorrect or out of date, or simply incomplete - we
consider all of those to be bugs; if you see them please raise an issue and
perhaps submit a pull request.

That's not much advice, but it's what we have so far.

------------
Using Sphinx
------------

We use `the Sphinx documentation system <http://sphinx-doc.org>`_ to run
doctests and convert the .rst files into html with formatting and
cross-references.  Without repeating the docs for Sphinx, here are some tips:

- When documenting a Python object (function, class, module, etc.), you can
  use autodoc to insert and interpret the docstring.

- When referencing a function, you can insert a reference to a function as
  (eg) ``:func:`hypothesis.given`\ ``, which will appear as
  ``hypothesis.given()`` with a hyperlink to the apropriate docs.  You can
  show only the last part (unqualified name) by adding a tilde at the start,
  like ``:func:`hypothesis.given`\ `` -> ``given()``.  Finally, you can give
  it alternative link text in the usual way:
  ``:func:`other text <hypothesis.given>`\ `` -> ``other text``.

- For the formatting and also hyperlinks, all cross-references should use the
  Sphinx cross-referencing syntax rather than plain text.

- Wherever possible, example code should be written as a doctest.  This
  ensures that if the example raises deprecation warnings, or simply breaks,
  it will be flagged in CI and can be fixed immediately.


-----------------
Changelog Entries
-----------------

`Hypothesis does continuous deployment <https://github.com/HypothesisWorks/hypothesis-python/issues/555>`_,
where every pull request that touches ``./src`` results in a new release.
That means every contributor gets to write their changelog!

A changelog entry should:

- concisely describe what changed and why
- use Sphinx cross-references to any functions or classes mentioned
- include the current date and proposed version number (also updated in src/hypothesis/version.py)
- if closing an issue, mention it with the issue role to generate a link
- finish with a note of thanks from the maintainers:
  "Thanks to <your name> for this bug fix / feature / contribution"
  (depending on which it is).  If this is your first contribution,
  don't forget to add yourself to contributors.rst!
