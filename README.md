# AnthemTool

AnthemTool is an unpacker made in python that can extract game resources 
from the Anthem game (which is based on the Frostbite Engine).

We are sharing this tool hoping the community can improve and build on 
this to provide more insight in the internals of the game.

This tool only runs on Windows as it depends on an external proprietary 
Oodle DLL (included with the game files) to perform file decompression.

## Features
 - Parsing the game data files (.sb, .toc, .cas)
 - Decompression of EBX, RES, CHUNKS and TOC Resources
 - Exporting everything to the local filesystem

## Quickstart

*AnthemTool requires python 3.6+ x86_64 to be installed.*

Install **anthemtool** from a terminal or PowerShell using GIT:

```
git clone https://github.com/xyrin88/anthemtool.git
cd anthemtool
```

Alternatively, you can download this git repository as a ZIP file, extract it
and open a terminal or PowerShell and navigate to the extracted folder.

Install the anthemtool library:
```
python setup.py install
```

Now open up `scripts/config.py` and configure at least the `GAME_FOLDER` and 
`OUTPUT_FOLDER`. 

##### *Export all files to the configured `OUTPUT_FOLDER`*
```
python scripts/export.py
```

Keep in mind that extraction can take a long time depending on the processing
power available and how fast your disk is. We recommend exporting to an SSD
as this will greatly reduce the total time required to complete the export.
For us it took around 30 minutes on a fairly recent pc. You will need around 
75GB of free disk space to store approximately 290k files.

During the export, warnings may appear indicating that some bundles are 
unavailable. This is expected behavior as not all language bundles are 
distributed along with the game files by default. You can safely ignore this 
message.


## Known Issues

### Script crashes with a `Could not load Oodle DLL` exception

This is most likely caused by using a 32-bit version of python. The Oodle DLL
that is loaded to perform the file decompression requires a 64bit process.

To resolve this issue, install the 64bit version of python 3.

### Script crashes with a `FileNotFoundError`

This is probably caused by export file paths exceeding the default Win32 path
limit of 260 characters. You have two options:

 1. Prepend ` \\?\ ` to the `OUTPUT_FOLDER` in `scripts/config.py`.

    Example: `OUTPUT_FOLDER = r"\\?\C:\AnthemExport"`
    
 2. Enable Win32 Long Path support (via Group Policy Editor). 


## Troubleshooting
When running into issues, logging can be configured in `scripts/config.py` to 
get additional debug output.

The `scripts/export.py` script consists of two phases:
 - Frostbite Game initialization (this will collect all the game meta data)
 - File export (this will iterate over all file parts and start decompression)

When you want to debug code from phase two it really helps to enable caching,
as this will save a cached version of the Frostbite Game so it can be loaded 
quickly from the cache.

If you want to make changes to the library code (inside the anthemtool folder),
you need to make sure the code is imported directly instead of the installed 
package. The easiest way to do this is to run `python setup.py develop`.  

## Technical Notes

This tool is based entirely on the structure of the files for Anthem and will 
therefore likely not work out of the box with other Frostbite games. 
Due to our lack of knowledge of the Frostbite data structure, some model 
designs will likely not match the original specification.

Regardless of this we will try to explain what we understand of the data 
formats anyway and how we interpret them.

While reading the notes below, please keep in mind that parts of it might
not be entirely accurate.


### Anthem Game Folder structure

The game folder structure for Anthem looks as follows (some items have been 
omitted to improve readability).

 ```
  . 
  |-- Data                                       <-- primary layout
  |   |-- layout.toc                             <-- layout description
  |   |-- Win32
  |   |   |-- conversationperformances.sb        <-- superbundle
  |   |   |-- conversationperformances.toc       <-- superbundle index
  |   |   |-- default.sb
  |   |   |-- default.toc
  |   |   |-- forttarsis.sb
  |   |   |-- forttarsis.toc
  |   |   |-- globals.sb
  |   |   |-- globals.toc
  |   |   |-- launch
  |   |   |   |-- music.sb
  |   |   |   |-- music.toc
  |   |   |-- levels
  |   |   |   |-- boot
  |   |   |   |   |-- boot.sb
  |   |   |   |   |-- boot.toc
  |   |   |   |-- root
  |   |   |   |   |-- root.sb
  |   |   |   |   |-- root.toc
  |   |   |-- loc
  |   |   |   |-- en.sb
  |   |   |   |-- en.toc
  |   |   |-- loctext
  |   |   |   |-- en.sb
  |   |   |   |-- en.toc
  |   |   |-- music.sb
  |   |   |-- music.toc
  |   |   |-- streaminginstall                   <-- install chunk root
  |   |   |   |-- dylandefaultinstallpackage     <-- install chunk / package
  |   |   |   |   |-- en
  |   |   |   |   |   |-- loc
  |   |   |   |   |   |   |-- en.sb
  |   |   |   |   |   |   |-- en.toc
  |   |   |   |   |-- default.sb                 <-- split superbundle
  |   |   |   |   |-- default.toc                <-- split superbundle index
  |   |   |   |   |-- cas_01.cas                 <-- cas data archive file
  |   |   |   |   |-- cas_02.cas
  |   |   |   |   |-- cas_03.cas
  |   |   |   |   |-- ...
  |   |   |   |-- dylanfinalinstallpackage
  |   |   |   |   |-- ...
  |   |   |   |-- dylanforttarsisinstallpackage
  |   |   |   |   |-- ...
  |   |   |-- tutorials.sb
  |   |   |-- tutorials.toc
  |   |   |-- ui.sb
  |   |   |-- ui.toc
  |-- Patch                                      <-- secondary layout
  |   |-- ...
  |-- ...
 ```
 
### TOC files

The purpose of the TOC (Table of Content) files is to describe what content 
can be found in the underlying data structure. 

For example, layout.toc contains information about the available installation 
chunks (packages), how they depend on each other and what bundles they contain. 

In the case of superbundles, TOC files always come with an associated .sb file.
The TOC file contains the meta data of the bundles and specifies where the data
of them can be found in the corresponding .sb file. 
In addition to this, it also contains references to file parts which we call
TOC resources.

TOC files always start with magic 0x00D1CE01 and the data section starts at
0x22C. In case of superbundle TOC files the data section appears to be wrapped
inside another container format that starts with magic 0x00000030.

### SB files

A superbundle represents a collection of files that the game engine uses to 
render the game. Think of textures, animations, sound files, scripts, etc.

Each SB file contains meta data about the file parts that make up the 
bundle. These parts are split into 3 different categories: Ebx, Resources and 
Chunks. All three come with the following information:
 - SHA1 sum (seems to act as a unique file identifier)
 - CAS identifier (refer to the CAS section below)
 - CAS offset
 - Compressed size
 - Flags (some kind of meta data)
 
Ebx and Resource parts also contain a filename and the uncompressed size.
Resource parts also provide information about the content type and have some 
extra meta data.
Chunks do not have a filename but provide a UID and also some extra meta data.

There are both superbundles and split superbundles. A split superbundle is
directly tied to an installation chunk (package), while a regular superbundle
is shared.

SB files appear to start with a container structure with magic 0x00000020.

### CAS files

CAS files contain the actual file data (think of them as ZIP archives).

When TOC or SB files want to refer to file data, they do so by specifying a
CAS identifier, a CAS offset and the size of the compressed file.

To figure out which CAS holds the given file, we look at the 32bit 
CAS identifier which contains the following information:
 - Layout ID (0 for Data, 1 for Patch)
 - Installation Chunk / Package ID (index in layout.toc)
 - CAS file index (1 -> cas_01.cas, 2 -> cas_02.cas, etc)
 
We can now seek to the CAS offset in the corresponding CAS file and decompress
until we read as much as the specified compressed size. The compressed file is
split into chunks of 0x10000 bytes. Each chunk starts with an 8 byte header 
that contains the size of the chunk, the uncompressed size of the chunk, and 
the type of compression used.

Currently we interpret the compression part as a 16bit integer and came 
across the values 0x1170, 0x70 and 0x71. The first one indicates it has been
compressed using Oodle and the latter two appear to be uncompressed. This 
leads us to believe that this 16bit value can be broken down further into
more specific bit values (but are unsure how specifically).

We also have not found a way to verify if file parts with value 0x70 or 
0x71 are exported correctly. Additional changes to the export logic for these
parts might still be necessary.
 
## Acknowledgements

This tool has been made possible by a lot of community info on Frostbite and 
tools provided by others.

A special thanks to the following resources:
 - https://forum.xentax.com/
 - https://github.com/mitsuhiko/frostbite2-stuff
 - https://github.com/NicknineTheEagle/Frostbite-Scripts
 - Bf4 Sbtoc Dumper
 - swbf2_bfv_dumper

## Contributing

We welcome others to further improve this tool or to share code that can help
parsing the resulting resource files. All feedback and knowledge will be
highly appreciated. Do not hesitate to send us an email at
**xyrin88[at]gmail[dot]com**.

## License

See the [LICENSE](LICENSE.md) file for license rights and limitations (MIT).
