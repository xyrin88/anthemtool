import binascii
from uuid import UUID
from typing import Optional

from anthemtool.cas.cas import Cas
from anthemtool.cas.types import RESOURCE_TYPES


class File:
    """
    Base for all data files that reside in CAS files.
    """

    def __init__(self,
                 sha1: Optional[bytes] = None,
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
            binascii.hexlify(self.sha1).decode('utf-8') if self.sha1 else '0',
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

        if self.sha1:
            return binascii.hexlify(self.sha1).decode('utf-8') + ".bin"

        raise Exception("Could not produce a unique filename for {}".format(self))

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
                 sha1: Optional[bytes] = None,
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
        ext = self.content_type or '.res_{:x}'.format(self.content_type_id or 0x0)

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


class TocResource(File):
    """
    TocResource is a data file with an identifier and not tied to a bundle.
    """

    def __init__(self,
                 uid,
                 sha1: Optional[bytes] = None,
                 cas: Optional[Cas] = None,
                 name: Optional[str] = None,
                 flags: Optional[int] = None,
                 offset: Optional[int] = None,
                 size: Optional[int] = None,
                 orig_size: Optional[int] = None) -> None:
        """
        Initialize instance.
        """
        super().__init__(sha1, cas, name, flags, offset, size, orig_size)
        self.uid = uid

    @property
    def guid(self) -> UUID:
        """
        Get the GUID for this instance.
        """
        return UUID(bytes_le=self.uid[::-1])

    @property
    def filename(self) -> str:
        """
        Get the filename that represents this instance.
        """
        return str(self.guid) + ".chunk"

    def _format(self) -> str:
        """
        Create a human readable representation of this instance.
        """
        value = 'guid=0x{:s}, '

        return value.format(str(self.guid)) + super()._format()


class Chunk(TocResource):
    """
    Chunk is a data file with an identifier instead of a filename.
    """

    def __init__(self,
                 uid: bytes,
                 range_start: int,
                 logical_size: int,
                 logical_offset: int,
                 sha1: Optional[bytes] = None,
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
        super().__init__(uid, sha1, cas, name, flags, offset, size)
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
    def guid(self) -> UUID:
        return UUID(bytes=self.uid)

    def _format(self) -> str:
        """
        Create a human readable representation of this instance.
        """
        value = 'range_start=0x{:x}, logical_size=0x{:x}, ' \
                'logical_offset=0x{:x}, h32=0x{:x}, first_mip=0x{:x}, '

        return value.format(
            self.range_start,
            self.logical_size,
            self.logical_offset,
            self.h32 or 0x0,
            self.first_mip or 0x0,
        ) + super()._format()

