RELEASE_TYPE: patch

This release makes Hypothesis's memory usage substantially smaller for tests with many
examples, by bounding the number of past examples it keeps around. 

You will not see much difference unless you are running tests with :obj:`~hypothesis.settings.max_examples`
set to well over ``1000``, but if you do have such tests then you should see memory usage mostly plateau
where previously it would have grown linearly with time.
