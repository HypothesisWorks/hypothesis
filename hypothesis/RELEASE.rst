RELEASE_TYPE: patch

This patch corrects the parameter names of the methods on
:func:`~hypothesis.strategies.data`, so that passing an argument by keyword -
for example ``st.data().map(pack=str)`` - raises the intended
:class:`~hypothesis.errors.InvalidArgument` instead of a confusing
``TypeError`` about an unexpected keyword argument (:issue:`4889`).

Thanks to kokokoXUY for this fix!
