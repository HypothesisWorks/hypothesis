RELEASE_TYPE: minor

:func:`~hypothesis.strategy.from_regex` now supports the atomic grouping
(``(?>...)``) and possessive quantifier (``*+``, ``++``, ``?+``, ``{m,n}+``)
syntax `added in Python 3.11 <https://docs.python.org/3/whatsnew/3.11.html#re>`__.

Thanks to Cheuk Ting Ho for implementing this!
