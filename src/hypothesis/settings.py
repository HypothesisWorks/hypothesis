class Settings(object):
    def __init__(
        self,
        min_satisfying_examples=None,
        max_examples=None,
        max_skipped_examples=None,
        timeout=None,
        derandomize=None,
    ):
        self.min_satisfying_examples = (
            min_satisfying_examples or default.min_satisfying_examples)
        self.max_examples = max_examples or default.max_examples
        self.timeout = timeout or default.timeout
        self.max_skipped_examples = (
            max_skipped_examples or default.max_skipped_examples)
        if derandomize is None:
            self.derandomize = default.derandomize
        else:
            self.derandomize = derandomize


default = Settings(
    min_satisfying_examples=5,
    max_examples=200,
    timeout=60,
    max_skipped_examples=50,
    derandomize=False,
)
