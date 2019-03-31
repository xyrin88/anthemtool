import binascii
from typing import Optional

from anthemtool.cas.cas import Cas
from anthemtool.cas.types import RESOURCE_TYPES


class File:
    """
    Base for all data files that reside in CAS files.
    """

    def __init__(self,
                 sha1: bytes,
                 cas: Optional[Cas] = None,
                 name: Optional[str] = None,
                 flags: Optional[int] = None,
                 offset: Optional[int] = None,
                 size: Optional[int] = None,
                 orig_size: Optional[int] = None) -> None:
        """
        Initialize instance.
        """
        self.cas = cas
        self.name = name
        self.sha1 = sha1
        self.flags = flags
        self.offset = offset
        self.size = size
        self.orig_size = orig_size

    def _format(self) -> str:
        """
        Create a human readable representation of this instance.
        """
        value = 'name={}, cas={}, sha1=0x{}, offset=0x{:x}, ' \
                'size=0x{:x}, orig_size=0x{:x}, flags=0x{:x}'

        return value.format(
            self.name,
            self.cas.path if self.cas else None,
            binascii.hexlify(self.sha1).decode('utf-8'),
            self.offset or 0x0,
            self.size or 0x0,
            self.orig_size or 0x0,
            self.flags or 0x0,
        )

    @property
    def filename(self) -> str:
        """
        Get the filename that represents this instance.
        """
        if self.name:
            return self.name + ".bin"

        return binascii.hexlify(self.sha1).decode('utf-8') + ".bin"

    def __repr__(self) -> str:
        return '{}({})'.format(self.__class__.__name__, self._format())


class Ebx(File):
    """
    Ebx data file. Commonly referenced in bundles.
    """

    @property
    def filename(self) -> str:
        """
        Get the filename that represents this instance.
        """
        if self.name:
            return self.name + '.ebx'

        return super().filename


class Resource(File):
    """
    Resource is a data file that provides additional content type information.
    """

    def __init__(self,
                 sha1: bytes,
                 cas: Optional[Cas] = None,
                 name: Optional[str] = None,
                 flags: Optional[int] = None,
                 offset: Optional[int] = None,
                 size: Optional[int] = None,
                 orig_size: Optional[int] = None,
                 content_type_id: Optional[int] = None,
                 meta: Optional[bytes] = None,
                 rid: Optional[int] = None) -> None:
        """
        Initialize instance.
        """
        super().__init__(sha1, cas, name, flags, offset, size, orig_size)
        self.content_type_id = content_type_id
        self.meta = meta
        self.rid = rid

    @property
    def content_type(self) -> Optional[str]:
        """
        Find the content type based on the content type id.
        """
        if self.content_type_id and self.content_type_id in RESOURCE_TYPES.keys():
            return RESOURCE_TYPES[self.content_type_id]

        return None

    @property
    def filename(self) -> str:
        """
        Get the filename that represents this instance.
        """
        name = self.name or binascii.hexlify(self.sha1).decode('utf-8')
        ext = self.content_type or '.res'

        return name + ext

    def _format(self) -> str:
        """
        Create a human readable representation of this instance.
        """
        value = ', content_type_id=0x{:x}. content_type={}, meta=0x{:s}, rid=0x{:x}'

        return super()._format() + value.format(
            self.content_type_id or 0x0,
            self.content_type,
            binascii.hexlify(
                self.meta.strip(b'\x00') or b'\x00'
            ).decode('utf-8') if self.meta else '0',
            self.rid or 0x0,
        )


class Chunk(File):
    """
    Chunk is a data file with an identifier instead of a filename.
    """

    def __init__(self,
                 sha1: bytes,
                 uid: bytes,
                 range_start: int,
                 logical_size: int,
                 logical_offset: int,
                 cas: Optional[Cas] = None,
                 name: Optional[str] = None,
                 flags: Optional[int] = None,
                 offset: Optional[int] = None,
                 size: Optional[int] = None,
                 h32: Optional[int] = None,
                 first_mip: Optional[int] = None) -> None:
        """
        Initialize instance.
        """
        super().__init__(sha1, cas, name, flags, offset, size)
        self.uid = uid
        self.range_start = range_start
        self.logical_size = logical_size
        self.logical_offset = logical_offset
        self.h32 = h32
        self.first_mip = first_mip

    @property
    def orig_size(self) -> Optional[int]:
        """
        Calculate the original size of the chunk.
        """
        return self.logical_offset + self.logical_size

    @orig_size.setter
    def orig_size(self, value: Optional[int] = None) -> None:
        """
        Do not allow setting this attribute as it is calculated.
        """
        return

    @property
    def filename(self) -> str:
        """
        Get the filename that represents this instance.
        """
        result = binascii.hexlify(self.sha1).decode('utf-8')
        if self.uid:
            result += "_{}".format(binascii.hexlify(self.uid).decode('utf-8'))

        return result + ".chunk"

    def _format(self) -> str:
        """
        Create a human readable representation of this instance.
        """
        value = 'id=0x{:s}, range_start=0x{:x}, logical_size=0x{:x}, ' \
                'logical_offset=0x{:x}, h32=0x{:x}, first_mip=0x{:x}, '

        return value.format(
            binascii.hexlify(self.uid).decode('utf-8') if self.uid else '0',
            self.range_start,
            self.logical_size,
            self.logical_offset,
            self.h32 or 0x0,
            self.first_mip or 0x0,
        ) + super()._format()
