RELEASE_TYPE: minor

This release makes it an explicit error to apply
:func:`@pytest.fixture <pytest:pytest.fixture>` to a function which has
already been decorated with :func:`@given() <hypothesis.given>`.  Previously,
``pytest`` would convert your test to a fixture, and then never run it.
