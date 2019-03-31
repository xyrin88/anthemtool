import logging

from struct import unpack
from typing import Optional, Dict

from anthemtool.cas.cas import Cas
from anthemtool.io.providers.base import Decompressor
from anthemtool.util import PathUtil


LOG = logging.getLogger(__name__)


class CasWriter:
    """
    Writer for CAS file entries.
    """

    DECOMPRESSION_LOOKUP = {
        0x70: 'null',
        0x71: 'null',
        0x1170: 'oodle',
    }

    def __init__(self, decompressors: Dict[str, Decompressor]) -> None:
        """
        Initialize instance.
        """
        self.decompressors = decompressors

    def write(self, cas: Cas, offset: int, path: str, compressed_file_size: int,
              file_size: Optional[int] = None) -> None:
        """
        Write the given entry to the output path.
        """
        # LOG.debug(
        #     "Writing cas=%s offset=0x%x size=0x%x outsize=0x%x to %s",
        #     cas, offset, compressed_file_size, file_size or 0x0, path
        # )

        PathUtil.ensure_base_path_exists(path)

        result_size = 0
        payload_size = 0

        # Get CAS file handle
        handle = cas.handle
        handle.seek(offset)

        # Open output file for writing
        with open(path, "wb") as dst:

            # Read until we reached the given compressed size
            while payload_size < compressed_file_size:
                size = unpack(">I", handle.read(4))[0]
                magic = unpack(">H", handle.read(2))[0]
                compressed_size = unpack(">H", handle.read(2))[0]

                # LOG.debug(
                #     "Writing part size=0x%x outsize=0x%x magic=0x%x",
                #     size, compressed_size, magic
                # )

                # Determine how to read based on the magic
                if magic == 0x1170:
                    # Oodle compression, read the compressed size
                    payload = handle.read(compressed_size)

                elif magic in (0x70, 0x71):
                    # We are not sure about these, but they appear to be parts that
                    # reside in the CAS file uncompressed.

                    # Size and compressed size seems to be the same for parts with magic 0x70
                    if magic == 0x70 and size != compressed_size:
                        raise Exception("Expected size=0x{:x} and outsize=0x{:x} to match".format(
                            size, compressed_size
                        ))

                    # For magic 0x71, compressed size seems to be always zero
                    if magic == 0x71 and compressed_size != 0x00:
                        raise Exception(
                            "Expected outsize=0x{:x} to be zero".format(compressed_size)
                        )

                    # Read uncompressed size
                    payload = handle.read(size)

                else:
                    # Other compression algorithms are not supported
                    raise Exception(
                        "Unsupported compression magic=0x{:x} size=0x{:x} outsize=0x{:x} (path={:s}"
                        " cas={} offset=0x{:x}, size=0x{:x}, outsize=0x{:x})".format(
                            magic, compressed_size, size, path, cas,
                            offset, compressed_file_size, file_size or 0x0
                        )
                    )

                # Invoke the appropriate decompressor
                decompressor = self.get_decompressor(magic)
                data = decompressor.decompress(payload, compressed_size, size)

                # Increment counters to keep track of progress
                result_size += len(data)
                payload_size += len(payload) + 8

                # Write the result to the disk
                dst.write(data)

                # LOG.debug(
                #     "File part written payload_size=0x%x total_payload_size=0x%x "
                #     "data_size=0x%x total_data_size=0x%x",
                #     len(payload), payload_size, len(data), result_size
                # )

        # LOG.debug(
        #     "Finished decompression payload_size=0x%x data_size=0x%x", payload_size, result_size
        # )

        # Make sure we read the exact amount of compressed bytes
        if payload_size != compressed_file_size:
            raise Exception(
                "Decompression failed, size requested=0x{:x} but got=0x{:x}".format(
                    compressed_file_size, payload_size
                )
            )

        # If we have a file_size, make sure it matches the length of the result
        if file_size is not None and result_size != file_size:
            raise Exception(
                "Decompression failed, outsize requested=0x{:x} but got=0x{:x}".format(
                    file_size, result_size
                )
            )

    def get_decompressor(self, magic: int) -> Decompressor:
        """
        Get the decompressor for the given magic.
        """
        if magic not in self.DECOMPRESSION_LOOKUP.keys():
            raise Exception("No decompression mapping defined for magic 0x{:x}".format(magic))

        key = self.DECOMPRESSION_LOOKUP[magic]
        if key not in self.decompressors.keys():
            raise Exception("No decompression implementation found for key {}".format(key))

        return self.decompressors[key]
