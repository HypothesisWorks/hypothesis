RELEASE_TYPE: minor

The :func:`~hypothesis.extra.lark.from_lark` strategy now accepts an ``alphabet=``
argument, which is passed through to :func:`~hypothesis.strategies.from_regex`,
so that you can e.g. constrain the generated strings to a particular codec.

In support of this feature, :func:`~hypothesis.strategies.from_regex` will avoid
generating optional parts which do not fit the alphabet.  For example,
``from_regex(r"abc|def", alphabet="abcd")`` was previously an error, and will now
generate only ``'abc'``.  Cases where there are no valid strings remain an error.
