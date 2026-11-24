## Gain dB 1.4.1

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

A small GUI follow-up to 1.4.0. Analysis numbers, tag formats and CLI output are unchanged.

### Fixed
- **Ctrl+A and Ctrl+V right after start went to the Target Volume box** instead of selecting files. The file list now has the focus when the window opens.
- **Changing the language could bring back a horizontal scroll bar.** When the new language needs wider columns, the window now widens too (within the screen, unless it is maximized), as it does when Maximizing features are turned on.
- Select All Files, Select No Files and Invert selection are now disabled while a job runs, as in the original mp3gain GUI.
- The Russian name of Language > System default now reads "Как в системе".

### Note on 1.4.0
- The one-time layout reset in 1.4.0 also resets the window position and the maximized state, not only the window size and column widths. Other settings are kept. 1.4.1 does not reset anything again.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- New automated tests: the start focus, the selection items while busy, and widening after a language change (and no widening when no column grew). macOS was not checked by hand.

### Download
- `GainDB-1.4.1-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
