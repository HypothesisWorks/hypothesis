import hypothesis.settings
from hypothesis.internal.filestorage import set_hypothesis_home_dir
from tempfile import mkdtemp

set_hypothesis_home_dir(mkdtemp())

hypothesis.settings.default.max_examples = 1000
hypothesis.settings.default.timeout = -1

try:
    import resource
    MAX_MEMORY = 10
    resource.setrlimit(resource.RLIMIT_DATA, (MAX_MEMORY, MAX_MEMORY))
except ImportError:
    pass
