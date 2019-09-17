RELEASE_TYPE: patch

This patch fixes a bug in strategy inference for :pypi:`attrs` classes where
Hypothesis would fail to infer a strategy for attributes of a generic type
such as ``Union[int, str]`` or ``List[bool]`` (:issue:`2091`).

Thanks to Jonathan Gayvallet for the bug report and this patch!
