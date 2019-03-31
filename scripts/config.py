import logging
import os

# Set to the root of the game folder
GAME_FOLDER = r"C:\Program Files (x86)\Origin Games\Anthem"

# Set to an empty dir where you want to save the exported files
OUTPUT_FOLDER = r"C:\AnthemExport"

# Set which resources should be exported by the export script
EXPORT_EBX = True
EXPORT_RESOURCES = True
EXPORT_CHUNKS = True
EXPORT_TOC_RESOURCES = True

# Logging
root = logging.getLogger()
root.setLevel(logging.INFO)
ch = logging.StreamHandler()
formatter = logging.Formatter('%(levelname)-7s %(name)-22s %(message)s')
ch.setFormatter(formatter)
root.addHandler(ch)

# Oodle DLL location
OODLE_PATH = os.path.join(GAME_FOLDER, "oo2core_7_win64.dll")

# Caching can be helpful to debug export code
CACHE_ENABLED = False
CACHE_PATH = os.path.join(OUTPUT_FOLDER, 'cache')
