RELEASE_TYPE: patch

This patch improves import-detection in :doc:`the Ghostwriter <ghostwriter>`
(:issue:`3884`), particularly for :func:`~hypothesis.strategies.from_type`
and strategies from ``hypothesis.extra.*``.

Thanks to <contributor's name or handle> for this <contribution/fix/feature>!

---

In the example above, "patch" on the first line should be replaced by
"minor" if changes are visible in the public API, or "major" if there are
breaking changes.  Note that only maintainers should ever make a major
release.

The remaining lines are the actual changelog text for this release,
which should:

- concisely describe what changed _in the public API_, and why.
  Internal-only changes can be documented as e.g. "This release improves
  an internal invariant." (the complete changelog for version 6.99.11)
- use ``double backticks`` for verbatim code,
- use Sphinx cross-references to any functions or classes mentioned:
  - :pypi:`package` for links to external packages.
  - :func:`package.function` for link to functions, where the link text will
    be ``package.function``, or :func:`~package.function` to show ``function``.
  - :class:`package.class` for link to classes (abbreviated as above).
  - :issue:`issue-number` for referencing issues.
  - Similarly, :pull:`pr-number` can be used for PRs, but it's usually
    preferred to refer to version numbers such as :ref:`version 6.98.9 <v6.98.9>,
    as they are meaningful to end users.
  - :doc:`link text <chapter#anchor>` for documentation references.
  - `link text <https://hypothesis.readthedocs.io/en/latest/chapter.html#anchor>`__
    is the same link, for general web addresses.
- finish with a note of thanks from the maintainers. If this is your first
  contribution, don't forget to add yourself to AUTHORS.rst!

After the PR is merged, the contents of this file (except the first line)
are automatically added to ``docs/changelog.rst``. More examples can be found
in that file.
