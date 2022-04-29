RELEASE_TYPE: patch
This release catches a ValueError when `importlib.abc.Traversable.read_text` attempts to read a DegenerateFile in python 3.10. To avoid raising this error we should fallback to using `importlib.resources.read_text`.

Note: `importlib.resources.read_text` is deprecated in python 3.10 and this error will resurface when python 3.8 support is dropped.

Thanks to Munir Abdinur for this contribution.
