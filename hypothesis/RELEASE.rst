RELEASE_TYPE: patch

This patch dramatically improves the performance of
:func:`~hypothesis.strategies.from_type` on hierarchies of abstract classes
whose subclasses refer back to the base class (directly, or via a sibling
subclass) in their annotations.  Resolution previously took time cubic in the
number of subclasses; we now resolve each type only once (:issue:`4729`).
