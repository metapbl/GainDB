## Gain dB 1.1.1

Lossless MP3 volume analysis and adjustment, a Python re-implementation refactored from a reading of the mp3gain source (LGPL-2.1-or-later).

Analysis numbers, tag formats and CLI output are unchanged from 1.1.0. This is a small GUI menu change.

### Changed
- **Re-calculate (do not read tags) moved up to the Options menu.** It was the only item in the Options > Tags submenu, so it now sits directly under Options, after "Don't clip when doing Track Gain". The name, behavior and saved setting are the same, so a setting turned on in 1.1.0 stays on.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- The menu position is covered by an automated test. macOS was not checked by hand.

### Download
- `GainDB-1.1.1-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
