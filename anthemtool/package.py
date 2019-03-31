import logging
import os
from typing import Optional, List, Dict, TYPE_CHECKING

from anthemtool.cas.cas import Cas
from anthemtool.toc.file import TocFile
from anthemtool.toc.index import TocIndex

if TYPE_CHECKING:
    from anthemtool.toc.layout import Layout


LOG = logging.getLogger(__name__)


class Package:
    """
    Represents an installation chunk that references (split) superbundles.
    Also maintains .cas files which are the archives for the data files.
    """

    def __init__(self,
                 layout: 'Layout',
                 idx: int,
                 path: str,
                 parent: Optional['Package'] = None,
                 superbundles: Optional[List[str]] = None,
                 splitsuperbundles: Optional[List[str]] = None) -> None:
        """
        Initialize instance.
        """
        self.layout = layout
        self.idx = idx
        self.path = path
        self.parent = parent

        # Local entries
        self.cas_files: List[Cas] = []
        self.superbundles: Dict[str, Optional[TocIndex]] = {}
        self.splitsuperbundles: Dict[str, Optional[TocIndex]] = {}

        # Load the package
        self.load(superbundles, splitsuperbundles)

    def load(self,
             superbundles: Optional[List[str]],
             splitsuperbundles: Optional[List[str]]) -> None:
        """
        Initialize the given bundles and discover all CAS files.
        """
        package_root = os.path.join(self.layout.game.path, self.layout.path, self.path)
        if not os.path.exists(package_root):
            LOG.warning("Package %s unavailable", package_root)
            return

        LOG.debug("Loading package from %s", package_root)

        # Load CAS files if they exist
        self.cas_files = self.get_cas_files(package_root)

        # Splitsuperbundles exist in the same folder as the current package
        if splitsuperbundles:
            for splitsuperbundle in splitsuperbundles:
                name = splitsuperbundle[len('Win32/'):]
                bundle_path = os.path.join(package_root, name)

                LOG.debug("Initializing split superbundle %s", bundle_path)
                self.splitsuperbundles[splitsuperbundle] = self.load_bundle(bundle_path)

        # Superbundles are located in the root of the layout folder
        if superbundles:
            for superbundle in superbundles:
                bundle_path = os.path.join(self.layout.game.path, self.layout.path, superbundle)

                LOG.debug("Initializing superbundle %s", bundle_path)
                self.superbundles[superbundle] = self.load_bundle(bundle_path)

    def load_bundle(self, path: str) -> Optional[TocIndex]:
        """
        Load the TocIndex and SBBundle from the given path.
        Returns None if the bundle is not included in the game files.
        """
        if not os.path.exists(path + ".toc"):
            LOG.warning("Superbundle %s unavailable", path)
            return None

        LOG.debug("Loading index and superbundle %s", path)

        toc_file = TocFile(path + ".toc")
        if not toc_file.data:
            raise Exception("Could not read data from bundle")

        bundle = open(path + ".sb", "rb")
        return TocIndex(self, bundle, toc_file.data)

    def has_package(self, idx: int) -> bool:
        """
        Determine if a package with the given id exists.
        """
        return idx == self.idx or idx in self.layout.packages.keys()

    def get_package(self, idx: int, is_patch: bool) -> 'Package':
        """
        Get the package for the given index and layout id.
        """
        package = self if idx == self.idx else self.layout.packages[idx]
        if not package:
            raise Exception("Package with idx {} not found".format(idx))

        # Assume this is the Patch layout if parent is set
        if not is_patch and package.parent is not None:
            package = package.parent

        return package

    def get_cas(self, value: int) -> Optional[Cas]:
        """
        Fetch the CAS file for the given CAS identifier.
        """
        package_index = value >> 8 & 0xFF
        cas_index = value & 0xFF
        is_patch = value >> 16

        if cas_index < 0x1:
            return None

        if is_patch not in (0x0, 0x1):
            return None

        if not self.has_package(package_index):
            return None

        package = self.get_package(package_index, is_patch == 0x1)
        if cas_index > len(package.cas_files):
            return None

        return package.cas_files[cas_index - 1]

    def get_cas_files(self, path: str) -> List[Cas]:
        """
        Discover the CAS files for the given path by traversing the directory structure.
        """
        cas_files = [
            Cas(self, os.path.join(path, f))
            for f in os.listdir(path) if Cas.is_valid_cas_file(os.path.join(path, f))
        ]

        return sorted(cas_files, key=lambda x: x.path)

    def __str__(self) -> str:
        return self.path
