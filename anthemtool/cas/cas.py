import os
from struct import unpack
from typing import BinaryIO, Dict, TYPE_CHECKING

if TYPE_CHECKING:
    from anthemtool.package import Package


class Cas:
    """
    Represents a CAS data file.

    A CAS file is an archive that holds multiple (compressed) files.
    """

    def __init__(self, package: 'Package', path: str) -> None:
        """
        Initialize instance.
        """
        self.package = package
        self.path = path

    def has_file_at(self, offset: int) -> bool:
        """
        Determine if the start of a file part exists at the given offset.
        """
        handle = self.handle
        handle.seek(offset + 0x4)
        magic = unpack(">H", handle.read(2))[0]

        return magic in (0x70, 0x71, 0x1170)

    @property
    def handle(self) -> BinaryIO:
        """
        Fetch the file handle from the CasCache.
        Decoupling file handles allows for serialization to support caching.
        """
        return CasCache.get_cas_handle(self.path)

    @staticmethod
    def is_valid_cas_file(path: str) -> bool:
        """
        Determine if the given file path is an actual CAS file.
        """
        if not os.path.isfile(path):
            return False

        return path.endswith('.cas')

    def __str__(self) -> str:
        return self.path


class CasCache:
    """
    Holds a cache of CAS file handles to allow for easy re-use.
    """

    handles: Dict[str, BinaryIO] = {}

    @staticmethod
    def get_cas_handle(path: str) -> BinaryIO:
        """
        Get a file handle to the given CAS path, or create it if it does not yet exist.
        """
        if path not in CasCache.handles.keys():
            CasCache.handles[path] = open(path, "rb")

        return CasCache.handles[path]
