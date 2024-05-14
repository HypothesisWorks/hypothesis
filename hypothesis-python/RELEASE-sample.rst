RELEASE_TYPE: patch

"patch" should be replaced by "minor" if changes are visible in the
public API, or "major" if there are breaking changes.

The remaining lines are the actual changelog text for this release,
which should:

- concisely describe what changed and why
- use ``double backticks`` for verbatim code
- use Sphinx cross-references to any functions or classes mentioned
  :pypi:`<package>` for package links
  :func:`<function>` for link to functions
  :func:`~<package.function>` for abbreviated link to functions
  :issue:`<issue number>` for issues
  A sample documentation link is below.
- finish with a note of thanks from the maintainers:
  "Thanks to <your name> for this bug fix / feature / contribution"
  (depending on which it is).  If this is your first contribution,
  don't forget to add yourself to AUTHORS.rst!

See also `the documentation <guides/documentation.rst#changelog-entries>`_
