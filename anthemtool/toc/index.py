import logging
from struct import unpack
from typing import BinaryIO, List, TYPE_CHECKING

from anthemtool.cas.resource import File
from anthemtool.sb.bundle import SBBundle
from anthemtool.util import ReadUtil

if TYPE_CHECKING:
    from anthemtool.package import Package


LOG = logging.getLogger(__name__)


class TocIndex:
    """
    TocIndex holds a list of bundles that are parsed into SBBundle instances.
    Additionally contains a set of resources that do not seem to have a filename.
    These are parsed into Resource instances.
    """

    def __init__(self, package: 'Package', bundle: BinaryIO, handle: BinaryIO) -> None:
        """
        Initialize instance and start reading from the given file handle.
        """
        self.package = package

        # Local entries
        self.bundles: List[SBBundle] = []
        self.resources: List[File] = []

        # Load index
        self.read(handle, bundle)

    def read(self, handle: BinaryIO, bundle: BinaryIO) -> None:
        """
        Read from the given TocFile file handle and parse it.
        During parsing some extra checks make sure the parsing is performed correctly.
        """
        magic = unpack(">I", handle.read(4))[0]
        if magic != 0x30:
            raise Exception("Expected TocIndex magic 0x30 but got 0x{:x}".format(magic))

        # Parse container meta data
        handle.read(4)  # length
        item_count = unpack(">I", handle.read(4))[0]
        offset1 = unpack(">I", handle.read(4))[0]
        offset2 = unpack(">I", handle.read(4))[0]
        res_count = unpack(">I", handle.read(4))[0]
        offset4 = unpack(">I", handle.read(4))[0]
        offset5 = unpack(">I", handle.read(4))[0]
        offset6 = unpack(">I", handle.read(4))[0]
        handle.read(4)  # offset 7
        handle.read(4)  # sec4_size

        if item_count == 0:
            LOG.debug("TocIndex contains no bundles")
            return

        LOG.debug("TocIndex contains %d items", item_count)

        # Ref for each bundle (appear to be some kind of flags?)
        bundle_refs = [unpack(">I", handle.read(4))[0] for i in range(item_count)]

        # Alignment
        handle.read(4)
        while handle.tell() % 8 != 0:
            handle.read(1)

        # Process bundles
        for ref in bundle_refs:
            string_off = unpack(">I", handle.read(4))[0]
            size = unpack(">I", handle.read(4))[0]
            handle.read(4)  # unknown
            offset = unpack(">I", handle.read(4))[0]
            name = ReadUtil.read_string_rewind(handle, offset6 + string_off)

            self.bundles.append(
                SBBundle(self, bundle, offset, name, size, ref=ref)
            )

        # Read bundle resources
        res = []
        handle.seek(offset1)
        for idx in range(0, res_count):
            res.append({"flags": unpack(">I", handle.read(4))[0]})

        if handle.tell() != offset2:
            raise Exception("Toc parsing failed, expected offset2")

        # Read bundle resources sha1 entries
        for idx in range(0, res_count):
            # Is this a SHA sum or are the last 8 bytes something else?
            res[idx]['sha1'] = handle.read(20)

        if handle.tell() != offset4:
            raise Exception("Toc parsing failed, expected offset4")

        rest = handle.read(offset5 - offset4)
        if rest:
            raise Exception("Toc parsing failed, unexpected data at offset4")

        if handle.tell() != offset5:
            raise Exception("Toc parsing failed, expected offset5")

        # Read bundle resources locations
        for idx in range(0, res_count):
            cas_id = unpack(">I", handle.read(4))[0]
            offset = unpack(">I", handle.read(4))[0]
            size = unpack(">I", handle.read(4))[0]

            cas = self.package.get_cas(cas_id)
            if not cas:
                raise Exception("Could not find CAS entry for CAS identifier 0x{:x}".format(cas_id))

            self.resources.append(
                File(
                    cas=cas,
                    sha1=res[idx]['sha1'],
                    flags=res[idx]['flags'],
                    offset=offset,
                    size=size,
                )
            )

        if handle.tell() != offset6:
            raise Exception("Toc parsing failed, expected offset6")
