RELEASE_TYPE: minor

:func:`~hypothesis.strategies.fixed_dictionaries` now varies the iteration
order of the dicts it generates, rather than always placing the required keys
first, to help find bugs in code which is sensitive to key order
(:issue:`3906`). If you need a stable order, we recommend using `fixed_dictionaries(...).map(stable_sort_function)` or similar.
