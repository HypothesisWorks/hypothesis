RELEASE_TYPE: patch

This patch fixes a bug where ``text(...).filter(re.compile(...).match)``
could generate non-matching instances if the regex pattern contained ``|``
(:issue:`4008`).
