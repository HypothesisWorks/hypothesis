# pylint: skip-file
import sys
import struct

PY3 = sys.version_info[0] == 3

if PY3:
    text_type = str
    binary_type = bytes
    hrange = range
    ARG_NAME_ATTRIBUTE = 'arg'
    integer_types = (int,)
    hunichr = chr
else:
    text_type = unicode
    binary_type = str
    from __builtin__ import xrange as hrange
    ARG_NAME_ATTRIBUTE = 'id'
    integer_types = (int, long)

    def hunichr(i):
        try:
            return unichr(i)
        except ValueError:
            return struct.pack('i', i).decode('utf-32')
