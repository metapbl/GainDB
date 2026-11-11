## Gain dB 1.1.2

Lossless MP3 volume analysis and adjustment, a Python re-implementation refactored from a reading of the mp3gain source (LGPL-2.1-or-later).

Analysis numbers, tag formats and CLI output are unchanged from 1.1.1. This is a small GUI log fix.

### Fixed
- **The analysis log records each file once.** Running Track Analysis again on a file that already has values no longer adds another line to the analysis log, as in the original mp3gain. A file is logged again after Clear Analysis, Remove Tags or a tag rescan.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- The one-line log is covered by an automated test. The original mp3gain GUI's behavior was checked by hand on Windows.

### Download
- `GainDB-1.1.2-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
