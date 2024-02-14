RELEASE_TYPE: patch

This patch improves argument-to-json conversion for :doc:`observability <observability>`
output.  Checking for a ``.to_json()`` method on the object *before* a few other
options like dataclass support allows better user control of the process (:issue:`3880`).
