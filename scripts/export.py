import logging
import os
from typing import Dict, Optional

from diskcache import Cache

import config
from anthemtool.cas.resource import File
from anthemtool.game import FrostbiteGame
from anthemtool.io.providers.null import NullDecompressor
from anthemtool.io.providers.oodle import OodleDecompressor
from anthemtool.io.writer import CasWriter
from anthemtool.toc.index import TocIndex
from anthemtool.toc.layout import Layout
from anthemtool.util import PathUtil


LOG = logging.getLogger(__name__)


class Exporter:
    """
    Provides export functionality to dump the game resources to the local disk.
    """

    def __init__(self) -> None:
        """
        Initialize instance and prepare CasWriter.
        """
        if not os.path.exists(config.GAME_FOLDER):
            raise Exception("Could not open {}, check your config".format(config.GAME_FOLDER))

        try:
            PathUtil.ensure_path_exists(config.OUTPUT_FOLDER)
        except OSError as e:
            raise Exception(
                "Could not create output folder {}, check your config".format(config.OUTPUT_FOLDER)
            ) from e

        self.writer = CasWriter({
            'null': NullDecompressor(),
            'oodle': OodleDecompressor(config.OODLE_PATH),
        })

    def export(self) -> None:
        """
        Export the game files.
        """
        game = self.load_game()

        LOG.info("Starting export of files to %s", config.OUTPUT_FOLDER)
        self.export_layout(game.layout_data)
        self.export_layout(game.layout_patch)
        LOG.info("Export completed successfully")

    def export_layout(self, layout: Layout) -> None:
        """
        Export the given Layout instance.
        """
        LOG.info("Processing layout %s", layout)
        for key, package in layout.packages.items():
            LOG.info("Exporting package %s:%s", key, package)
            self.export_superbundles(package.splitsuperbundles)
            self.export_superbundles(package.superbundles)

    def export_superbundles(self, superbundles: Dict[str, Optional[TocIndex]]) -> None:
        """
        Process the given superbundles and export its items.
        """
        for name, index in superbundles.items():
            if not index:
                LOG.warning("Skipping unavailable superbundle %s", name)
                continue

            LOG.info("Exporting superbundle %s", name)
            for bundle in index.bundles:
                LOG.debug("Exporting bundle %s", bundle)

                if config.EXPORT_EBX:
                    for ebx in bundle.ebx:
                        self.export_resource(ebx, ebx.filename)

                if config.EXPORT_RESOURCES:
                    for resource in bundle.resources:
                        self.export_resource(resource, resource.filename)

                if config.EXPORT_CHUNKS:
                    for chunk in bundle.chunks:
                        self.export_resource(chunk, os.path.join(bundle.name, chunk.filename))

            if config.EXPORT_TOC_RESOURCES:
                for item in index.resources:
                    self.export_resource(item, os.path.join('TocResources', name, item.filename))

    def export_resource(self, item: File, path: str) -> None:
        """
        Export resource to a local file.
        """
        if not item.cas:
            raise Exception("File {} does not have a CAS file registered".format(item))

        if item.offset is None or item.size is None:
            raise Exception("File {} is missing an offset or size".format(item))

        # path = os.path.join(item.cas.package.path, item.filename)
        path = os.path.join(config.OUTPUT_FOLDER, item.cas.package.layout.path, path)
        if os.path.exists(path):
            LOG.debug("Skipping existing file %s", path)
            return

        LOG.debug("Reading %s", item)
        LOG.debug("Writing %s", path)
        self.writer.write(item.cas, item.offset, path, item.size, item.orig_size)

    def load_game(self) -> FrostbiteGame:
        """
        Load the game.
        """
        LOG.info("Loading game from %s", config.GAME_FOLDER)
        return FrostbiteGame(config.GAME_FOLDER)


class CacheExporter(Exporter):
    """
    Exporter implementation that attempts to load the game from the cache.
    """

    CACHE_KEY_GAME: str = "game"

    def __init__(self, cache_path: str) -> None:
        """
        Initialize instance.
        """
        super().__init__()
        self.cache_path = cache_path

    def load_game(self) -> FrostbiteGame:
        """
        Load the game from the cache, or reinitialize if it does not exists.
        """
        cache = Cache(self.cache_path)

        LOG.info("Loading game from cache")
        fbg = cache.get(self.CACHE_KEY_GAME)
        if not fbg or not isinstance(fbg, FrostbiteGame):
            LOG.info("Cache entry invalid or not found, reinitializing..")
            fbg = super().load_game()
            cache.set(self.CACHE_KEY_GAME, fbg)

        return fbg


if __name__ == "__main__":
    # Initialize the appropriate exporter
    exporter = CacheExporter(config.CACHE_PATH) if config.CACHE_ENABLED else Exporter()

    # Start exporting all files
    exporter.export()
