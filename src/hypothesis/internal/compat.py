# pylint: skip-file
import sys

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = 'arg'
    integer_types = (int,)
else:
    text_type = unicode
    binary_type = str
    from __builtin__ import xrange as hrange
    ARG_NAME_ATTRIBUTE = 'id'
    integer_types = (int, long)
