import binascii
import os
import logging
from typing import Dict, Optional, TYPE_CHECKING

from anthemtool.package import Package
from anthemtool.toc.entry import TocEntry
from anthemtool.toc.file import TocFile

if TYPE_CHECKING:
    from anthemtool.game import FrostbiteGame


LOG = logging.getLogger(__name__)


class Layout:
    """
    Specifies the included installation chunks and which bundles they contain.
    For each installation chunk a Package instance is initialized.
    """

    def __init__(self, game: 'FrostbiteGame', path: str, parent: Optional['Layout'] = None,
                 name: str = 'layout.toc') -> None:
        """
        Initialize instance and start reading the layout file.
        """
        self.game = game
        self.path = path
        self.name = name
        self.parent = parent

        # Local entries
        self.packages: Dict[int, Package] = {}

        # Load the layout
        self.read()

    def read(self) -> None:
        """
        Read the layout and create packages for all installation chunks.
        """
        layout_path = os.path.join(self.game.path, self.path, self.name)
        LOG.debug("Reading layout %s", layout_path)

        # Process install chunks
        source = TocEntry(TocFile(layout_path).data)
        for idx, chunk in enumerate(source.get('installManifest').get('installChunks')):
            chunk_id = binascii.hexlify(chunk.id).decode('utf-8')

            LOG.debug(
                "Processing install chunk id=0x%s name=%s bundle=%s",
                chunk_id,
                chunk.name,
                chunk.installBundle,
            )

            splitsuperbundles = [
                ss.get('superbundle') for ss in chunk.get('splitSuperbundles') or []
            ]

            superbundles = [
                s.get('data').decode('utf-8') for s in chunk.get('superbundles') or []
            ]

            self.packages[idx] = Package(
                self,
                idx,
                chunk.installBundle,
                parent=self.parent.packages[idx] if self.parent else None,
                splitsuperbundles=splitsuperbundles,
                superbundles=superbundles,
            )

    def __str__(self) -> str:
        return self.path
