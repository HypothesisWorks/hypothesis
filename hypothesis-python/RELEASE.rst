RELEASE_TYPE: patch

This release fixes a bug in explain mode where having [syrupy](https://github.com/syrupy-project/syrupy) installed
as a pytest plugin would cause it to erroneously show up as an explanation for errors.
