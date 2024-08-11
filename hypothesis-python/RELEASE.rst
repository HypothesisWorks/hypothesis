RELEASE_TYPE: minor

:ref:`alternative-backends` can now implement ``.observe_test_case()``
and ``observe_information_message()`` methods, to record backend-specific
metadata and messages in our :doc:`observability output <observability>`
(:issue:`3845` and `hypothesis-crosshair#22
<https://github.com/pschanely/hypothesis-crosshair/issues/22>`__).
