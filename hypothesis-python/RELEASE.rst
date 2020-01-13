RELEASE_TYPE: patch

This patch fixes :issue:`2320`, where ``from_type(Set[Hashable])`` could raise
an internal error because ``Decimal("snan")`` is of a hashable type, but raises
an error when hashed.  We now ensure that set elements and dict keys in generic
types can actually be hashed.
