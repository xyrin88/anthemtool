import logging
from struct import unpack
from typing import BinaryIO, Optional, Any

from anthemtool.util import ReadUtil


LOG = logging.getLogger(__name__)


class TocEntry:
    """
    Represents a single entry that is read from a TOC file.
    """

    def __init__(self, handle: Optional[BinaryIO] = None) -> None:
        """
        Initialize instance and start reading if we got a file handle.
        """
        if handle:
            self.read(handle)

    def read(self, handle: BinaryIO) -> None:
        """
        Read the entry from the given file handle.
        """
        item_type = handle.read(1)
        if item_type in (b'\x82', b'\x02'):
            if item_type == b'\x02':
                ReadUtil.read_string(handle)
            item_size = ReadUtil.read_leb(handle)
            item_offset = handle.tell()
            while handle.tell() - item_offset < item_size:
                self.add_field(handle)
        elif item_type == b'\x87':
            vars(self)['data'] = handle.read(ReadUtil.read_leb(handle) - 1)
            if handle.read(1) != b'\x00':
                raise Exception(
                    "Expected TocEntry at offset 0x{:x} to end with 0x00".format(handle.tell())
                )
        elif item_type == b'\x8f':
            vars(self)['data'] = handle.read(16)
        else:
            raise Exception(
                "Item type 0x{:x} at offset 0x{:x} not recognized".format(item_type, handle.tell())
            )

    def add_field(self, handle: BinaryIO) -> None:
        """
        Read one field from the given file handle.
        """
        offset = handle.tell()
        field_type = handle.read(1)
        if field_type == b'\x00':
            return

        key = ReadUtil.read_string(handle)
        if field_type == b'\x0f':
            vars(self)[key] = handle.read(16)
        elif field_type == b'\x09':
            vars(self)[key] = unpack("Q", handle.read(8))[0]
        elif field_type == b'\x08':
            vars(self)[key] = unpack("I", handle.read(4))[0]
        elif field_type == b'\x06':
            vars(self)[key] = handle.read(1) == b'\x01'
        elif field_type == b'\x02':
            handle.seek(offset, 0)
            vars(self)[key] = TocEntry(handle)
        elif field_type == b'\x13':
            vars(self)[key] = handle.read(ReadUtil.read_leb(handle))
        elif field_type == b'\x10':
            vars(self)[key] = handle.read(20)
        elif field_type == b'\x07':
            vars(self)[key] = handle.read(ReadUtil.read_leb(handle) - 1).decode('utf-8')
            handle.seek(1, 1)
        elif field_type == b'\x0c':
            vars(self)[key] = unpack(">Q", handle.read(8))[0]
        elif field_type == b'\x01':
            result = []
            list_size = ReadUtil.read_leb(handle)
            list_offset = handle.tell()
            while handle.tell() - list_offset < list_size - 1:
                result.append(TocEntry(handle))
            vars(self)[key] = result
            if handle.read(1) != b'\x00':
                raise Exception("Expected list at 0x{:x} to end with 0x00".format(handle.tell()))
        else:
            raise Exception(
                "Unknown field data type 0x{:x} at 0x{:x}".format(field_type, handle.tell())
            )

    def get(self, key: str) -> Any:
        """
        Return the member attribute value for the given key, or None if it does not exist.
        """
        return vars(self).get(key)
