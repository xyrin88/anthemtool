import logging
from struct import unpack
from typing import List, Any, BinaryIO, Tuple, TYPE_CHECKING

from anthemtool.cas.resource import Ebx, Resource, Chunk, File
from anthemtool.toc.entry import TocEntry
from anthemtool.util import ReadUtil

if TYPE_CHECKING:
    from anthemtool.toc.index import TocIndex


LOG = logging.getLogger(__name__)


class SBBundle:
    """
    Bundles contain multiple references to files that exist in CAS files:
     - Ebx
     - Resources
     - Chunks

    Each file reference provides at least the following data:
     - SHA1 sum
     - CAS file identifier (references a layout, package and cas index)
     - CAS offset
     - Compressed size

    Depending on the type of the file (Ebx, Resource, Chunk) some additional
    info is provided (Uncompressed Size, Name, ID, Content Type, etc).

    This class provides functionality to parse the .sb bundle and gives access to the files.
    """

    def __init__(self, index: 'TocIndex', bundle: BinaryIO, offset: int, name: str,
                 size: int, ref: int) -> None:
        """
        Initialize instance and start reading the sb at the given offset.
        """
        self.index = index
        self.name = name
        self.size = size
        self.ref = ref

        # Local entries
        self.files: List[File] = []
        self.ebx: List[Ebx] = []
        self.resources: List[Resource] = []
        self.chunks: List[Chunk] = []

        # Load bundle
        self.read(bundle, offset)

    def read(self, bundle: BinaryIO, offset: int) -> None:
        """
        Read from the given superbundle (.sb) file handle and parse it.
        During parsing some extra checks make sure the parsing is performed correctly.
        """
        LOG.debug("Reading bundle {} at offset 0x{:x}".format(self.name, offset))
        bundle.seek(offset)

        # Parse container data
        magic = unpack(">I", bundle.read(4))[0]
        if magic != 0x20:
            raise Exception("Expected TocIndex magic 0x20 but got 0x{:x}".format(magic))

        bundle.read(4)  # unknown
        bundle_len = unpack(">I", bundle.read(4))[0]
        bundle.read(4)  # count
        bundle.read(4)  # offset 1
        bundle.read(4)  # offset 2
        bundle.read(4)  # offset 3
        bundle.read(4)  # padding

        # Parse bundle data
        meta_size = unpack(">I", bundle.read(4))[0]
        meta_offset = bundle.tell()
        header = Header(unpack(">8I", bundle.read(32)))
        if header.magic != 0x9D798ED6:
            raise Exception("Invalid bundle magic")

        string_offset = meta_offset + header.string_offset

        # SHA1 hashes for all entries
        sha1_entries = [bundle.read(20) for i in range(header.total)]

        # Parse ebx entries
        self.ebx = [
            Ebx(
                sha1=sha1_entries[i],
                name=ReadUtil.read_string_rewind(
                    bundle, string_offset + unpack(">I", bundle.read(4))[0]
                ),
                orig_size=unpack(">I", bundle.read(4))[0],
            )
            for i in range(header.ebx)
        ]

        # Parse resource entries that have provide additional info
        self.resources = [
            Resource(
                sha1=sha1_entries[len(self.ebx) + i],
                name=ReadUtil.read_string_rewind(
                    bundle, string_offset + unpack(">I", bundle.read(4))[0]
                ),
                orig_size=unpack(">I", bundle.read(4))[0],
            )
            for i in range(header.resources)
        ]

        # Parse additional resource information
        for resource in self.resources:
            resource.content_type_id = unpack(">I", bundle.read(4))[0]

        for resource in self.resources:
            resource.meta = bundle.read(16)

        for resource in self.resources:
            resource.rid = unpack(">Q", bundle.read(8))[0]

        # Parse chunk entries that provide an ID instead of a name
        self.chunks = [
            Chunk(
                sha1=sha1_entries[len(self.ebx) + len(self.resources) + i],
                uid=bundle.read(16),
                range_start=unpack(">H", bundle.read(2))[0],
                logical_size=unpack(">H", bundle.read(2))[0],
                logical_offset=unpack(">I", bundle.read(4))[0],
            )
            for i in range(header.chunks)
        ]

        # Parse additional chunk meta data if available
        if header.chunks > 0:
            toc_entry = TocEntry()
            toc_entry.add_field(bundle)
            chunk_meta = toc_entry.get('chunkMeta')
        else:
            chunk_meta = []

        # Create a combined list of all entries
        self.files.extend(self.ebx)
        self.files.extend(self.resources)
        self.files.extend(self.chunks)

        # Skip parsing if we have no entries
        if header.total == 0:
            return

        # Parse the payload section that contains the CAS identifiers and offsets
        bundle.seek(meta_offset + meta_size)
        cas_id = unpack(">I", bundle.read(4))[0]
        for file in self.files:
            cas_id, addr = self.read_entry(cas_id, bundle)

            entry_cas = self.index.package.get_cas(cas_id)
            if not entry_cas:
                raise Exception("CAS instance for CAS identifier 0x{:x} not found".format(cas_id))

            file.offset = addr
            file.size = unpack(">I", bundle.read(4))[0]
            file.cas = entry_cas

        # Parse more additional chunk meta data
        for chunk_idx, chunk in enumerate(self.chunks):
            chunk.h32 = chunk_meta[chunk_idx].h32
            chunk.first_mip = chunk_meta[chunk_idx].meta.get('firstMip')

        # Make sure we parsed until the end of the payload
        if bundle.tell() - offset != bundle_len:
            raise Exception("Payload parsing error, check read_entry calls")

    def read_entry(self, cas_id: int, bundle: BinaryIO) -> Tuple[int, int]:
        """
        An entry exists of an offset but might also be prefixed with a CAS identifier.
        This seems a bit weird and we cannot figure out when to expect one or the other.

        To work around this, we check if the next value validates as a valid CAS identifier,
        and if so, perform an additional check to get rid of false positives (offsets that
        also pass validation). The second check is not completely reliable but appears to
        work fine in practice.
        """
        addr = unpack(">I", bundle.read(4))[0]

        # Check if addr could be a valid cas identifier
        cas = self.index.package.get_cas(addr)
        if cas:
            # Check if the addr is a valid entry in the previous cas
            prev_cas = self.index.package.get_cas(cas_id)
            if prev_cas and not prev_cas.has_file_at(addr):
                return addr, unpack(">I", bundle.read(4))[0]

        return cas_id, addr

    def __repr__(self) -> str:
        return self.name if self.name else 'Unknown'


class Header:
    """
    Header for SBBundle.
    """
    def __init__(self, values: Tuple[Any, ...]):
        self.magic = values[0]
        self.total = values[1]
        self.ebx = values[2]
        self.resources = values[3]
        self.chunks = values[4]
        self.string_offset = values[5]
        self.chunk_meta_offset = values[6]
        self.chunk_meta_size = values[7]
