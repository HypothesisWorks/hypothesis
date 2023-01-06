RELEASE_TYPE: patch

This patch brings our :func:`~hypothesis.provisional.domains` and
:func:`~hypothesis.strategies.emails` strategies into compliance with
:rfc:`RFC 5890 §2.3.1 <5890>`: we no longer generate parts-of-domains
where the third and fourth characters are ``--`` ("R-LDH labels"),
though future versions *may* deliberately generate ``xn--`` punycode
labels.  Thanks to :pypi:`python-email-validator` for `the report
<https://github.com/JoshData/python-email-validator/issues/92>`__!
