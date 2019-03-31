import abc


class Decompressor(abc.ABC):
    """
    Abstract interface for decompressor implementations.
    """
    @abc.abstractmethod
    def decompress(self, payload: bytes, size: int, output_size: int) -> bytes:
        """
        Decompress the given payload.
        """
        raise Exception("Not implemented")
