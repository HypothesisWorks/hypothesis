RELEASE_TYPE: patch

This patch ensures that, when the ``generate`` :obj:`~hypothesis.settings.phases`
is disabled, we can replay up to :obj:`~hypothesis.settings.max_examples` examples
from the database - which is very useful when
:ref:`using Hypothesis with a fuzzer <fuzz_one_input>`.

Thanks to Afrida Tabassum for fixing :issue:`2585`!