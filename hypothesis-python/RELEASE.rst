RELEASE_TYPE: patch

Adds a recipe to the docstring of :func:`~hypothesis.strategies.from_type`
that describes a means for drawing values for "everything except" a specified type.
This recipe is especially useful for writing tests that perform input-type validation.
