import os
from typing import BinaryIO


class ReadUtil:
    """
    Utility class for stream reading operations.
    """

    @staticmethod
    def read_leb(handle: BinaryIO) -> int:
        """
        Read an LEB128/7bit encoded integer.
        """
        result, i = 0, 0
        while True:
            byte = ord(handle.read(1))
            result |= (byte & 127) << i
            if byte >> 7 == 0:
                return result
            i += 7

    @staticmethod
    def read_string(handle: BinaryIO, encoding: str = 'utf-8') -> str:
        """
        Read a string from the given file handle.
        """
        result = b''

        while True:
            value = handle.read(1)
            if value == b'\x00':
                return result.decode(encoding)

            result += value

    @staticmethod
    def read_string_rewind(handle: BinaryIO, offset: int, encoding: str = 'utf-8') -> str:
        """
        Read a string at the given offset and rewind it.
        """
        pos = handle.tell()
        handle.seek(offset)
        result = ReadUtil.read_string(handle, encoding=encoding)
        handle.seek(pos)

        return result


class PathUtil:
    """
    Utility class for path operations.
    """

    @staticmethod
    def ensure_path_exists(path: str) -> None:
        """
        Recursively create the directory structure for the given path if it does not exist.
        """
        if not os.path.exists(path):
            os.makedirs(path)

    @staticmethod
    def ensure_base_path_exists(path: str) -> None:
        """
        Strip the filename of the given path and recursively create the directory structure.
        """
        base_path = os.path.dirname(path)
        PathUtil.ensure_path_exists(base_path)
