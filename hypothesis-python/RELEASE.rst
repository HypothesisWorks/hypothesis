RELEASE_TYPE: minor

:ref:`alternative-backends` can now implement a ``.get_observability_data()``
method, providing the ``x['metadata']['backend']`` dictionary in our
:doc:`observability output <observability>` (:issue:`3845` and `hypothesis-crosshair#22
<https://github.com/pschanely/hypothesis-crosshair/issues/22>`__).
