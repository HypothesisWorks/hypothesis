=====================================
The Hypothesis Documentation Handbook
=====================================

Note: Currently this guide is very specific to the *Python* version of Hypothesis.
It needs updating for the Ruby version (and, in future, other versions).

Good documentation can make the difference between good code and useful code -
and Hypothesis is written to be used, as widely as possible.

This is a working document-in-progress with some tips for how we try to write
our docs, with a little of the what and a bigger chunk of the how.
If you have ideas about how to improve these suggestions, meta issues or pull
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

We use `the Sphinx documentation system <http://sphinx-doc.org>`_ to
convert the .rst files into html with formatting and
cross-references.  Without repeating the docs for Sphinx, here are some tips:

- When documenting a Python object (function, class, module, etc.), you can
  use autodoc to insert and interpret the docstring.

- When referencing a function, you can insert a reference to a function as
  (eg) ``:func:`hypothesis.given`\``, which will appear as
  ``hypothesis.given()`` with a hyperlink to the appropriate docs.  You can
  show only the last part (unqualified name) by adding a tilde at the start,
  like ``:func:`~hypothesis.given`\ `` -> ``given()``.  Finally, you can give
  it alternative link text in the usual way:
  ``:func:`other text <hypothesis.given>`\ `` -> ``other text``.

- For the formatting and also hyperlinks, all cross-references should use the
  Sphinx cross-referencing syntax rather than plain text.


-----------------
Changelog Entries
-----------------

`Hypothesis does continuous deployment <https://github.com/HypothesisWorks/hypothesis-python/issues/555>`_,
where every pull request that touches ``./src`` results in a new release.
That means every contributor gets to write their changelog!

A changelog entry should be written in a new ``RELEASE.rst`` file in
the `hypothesis-python` directory, or ``RELEASE.md`` for the Ruby and Rust
versions.  Note that any change to ``conjecture-rust`` is automatically also
a change for our Ruby package, and therefore requires *two* release files!

The first line of the file specifies the component
of the version number that will be updated, according to our
`semantic versioning <https://semver.org/>`_ policy.

- ``RELEASE_TYPE: major`` is for breaking changes, and will only be used by the
  core team after extensive discussion.
- ``RELEASE_TYPE: minor`` is for anything that adds to the public (ie documented)
  API, changes an argument signature, or adds a new deprecation or health check.
  Minor (or patch) releases **must not** cause errors in any code that runs
  without errors on an earlier version of Hypothesis, using only the public API.
  Silent errors *may* be converted to noisy errors, but generally we prefer
  to issue a deprecation warning and use the new behaviour if possible.
  This stability policy only applies to use of Hypothesis itself, not the
  results of user-written tests that use Hypothesis.
- ``RELEASE_TYPE: patch`` is for changes that are not visible in the public
  interface, from improving a docstring to backwards-compatible improvements
  in shrinking behaviour.

This first line will be removed from the final change log entry.
The remaining lines are the actual changelog text for this release,
which should:

- concisely describe what changed and why
- use Sphinx cross-references to any functions or classes mentioned
- if closing an issue, mention it with the ``:issue:`` role to generate a link
- finish with a note of thanks from the maintainers:
  "Thanks to <your name> for this bug fix / feature / contribution"
  (depending on which it is).  If this is your first contribution,
  don't forget to add yourself to AUTHORS.rst!
