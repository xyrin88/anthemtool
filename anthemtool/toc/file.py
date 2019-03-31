import logging
from io import BytesIO
from struct import unpack
from typing import BinaryIO, Optional


LOG = logging.getLogger(__name__)


class TocFile:
    """
    Toc file handler for .toc files.
    """

    def __init__(self, path: str) -> None:
        """
        Initialize instance and start reading the TOC contents.
        """
        self.path: str = path

        # Local entries
        self.data: Optional[BinaryIO] = None

        # Load the data
        self.read()

    def read(self) -> None:
        """
        Open the toc file with the given path and read the contents at offset 0x22C.
        An exception is thrown if the file could not be parsed successfully.
        """
        LOG.debug("Reading TocIndex %s", self.path)
        with open(self.path, "rb") as handle:
            magic = unpack(">I", handle.read(4))[0]
            if magic != 0x00D1CE01:
                raise Exception("Expected TocIndex magic 0x00D1CE01 but got 0x{:x}".format(magic))

            handle.seek(0x22C)
            self.data = BytesIO(handle.read())
