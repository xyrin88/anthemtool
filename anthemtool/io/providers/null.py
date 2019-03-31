from anthemtool.io.providers.base import Decompressor


class NullDecompressor(Decompressor):
    """
    Null decompression implementation that just returns the untransformed input.
    """

    def decompress(self, payload: bytes, size: int, output_size: int) -> bytes:
        """
        Return the payload as output data.
        """
        return payload
