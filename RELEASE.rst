RELEASE_TYPE: patch

This release fixes dependency information when installing Hypothesis
from a binary "wheel" distribution.

- The ``install_requires`` for :pypi:`enum34` is resolved at install
  time, rather than at build time (with potentially different results).
- Django has fixed their ``python_requires`` for versions 2.0.0 onward,
  simplifying Python2-compatible constraints for downstream projects.
