import struct


class Reader(object):
    def __init__(self, buffer):
        self.__buffer = buffer
        self.__offset = 0

    def read(self, fmt):
        result = struct.unpack_from(fmt, self.__buffer, self.__offset)
        self.__offset += struct.calcsize(fmt)
        return result

    def assert_finished(self):
        assert len(self.__buffer) == self.__offset


class Writer(object):
    def __init__(self):
        self.buffer = bytearray()

    def write(self, fmt, *values):
        offset = len(self.buffer)
        self.buffer.extend(bytes(struct.calcsize(fmt)))
        struct.pack_into(fmt, self.buffer, offset, *values)
