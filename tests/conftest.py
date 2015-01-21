import hypothesis.settings
import resource

hypothesis.settings.default.max_examples = 1000
hypothesis.settings.default.timeout = 120

MAX_MEMORY = 10

resource.setrlimit(resource.RLIMIT_DATA, (MAX_MEMORY, MAX_MEMORY))
