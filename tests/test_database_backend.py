from hypothesis import given
from hypothesis.database.backend import SQLiteBackend
from hypothesis.internal.compat import text_type
from tests.common import small_verifier


@given([(text_type, text_type)], verifier=small_verifier)
def test_backend_returns_what_you_put_in(xs):
    backend = SQLiteBackend(":memory:")
    mapping = {}
    for key, value in xs:
        mapping.setdefault(key, set()).add(value)
        backend.save(key, value)
    for key, values in mapping.items():
        backend_contents = list(backend.fetch(key))
        distinct_backend_contents = set(backend_contents)
        assert len(backend_contents) == len(distinct_backend_contents)
        assert distinct_backend_contents == set(values)
