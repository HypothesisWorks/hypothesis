RELEASE_TYPE: minor

The ``unique_by`` argument to :obj:`~hypothesis.strategies.lists` now accepts a
tuple of callables such that every element of the generated list will be unique
with respect to each callable in the tuple (:issue:`1916`).

Thanks to Marco Sirabella for this feature at the PyCon 2019 sprints!
