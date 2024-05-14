RELEASE_TYPE: patch

"patch" should be replaced by "minor" if changes are visible in the
public API, or "major" if there are breaking changes.

The remaining lines are the actual changelog text for this release,
which should:

- concisely describe what changed and why
- use ``double backticks`` for verbatim code
- use Sphinx cross-references to any functions or classes mentioned
  :pypi:`package` for links to external packages
  :func:`package.function` for link to functions, or :func:`~package.function` for abbreviated link
  :class:`package.class` for link to classes (abbreviated: as above)
  :issue:`issue-number` for issues
  :doc:`link text <chapter#anchor>` for documentation references (``https://hypothesis.readthedocs.io/en/latest/<chapter>.html#<anchor>``)
- finish with a note of thanks from the maintainers:
  "Thanks to <your name> for this bug fix / feature / contribution"
  (depending on which it is).  If this is your first contribution,
  don't forget to add yourself to AUTHORS.rst!

Here's a concrete example:

This patch improves import-detection in :doc:`the Ghostwriter <ghostwriter>`
(:issue:`3884`), particularly for :func:`~hypothesis.strategies.from_type`
and strategies from ``hypothesis.extra.*``.
