## Gain dB 0.6.0

Lossless MP3 volume analysis and adjustment, a Python re-implementation refactored from a reading of the mp3gain source (LGPL-2.1-or-later).

### New
- **ffmpeg is found outside PATH too.** If `ffmpeg`/`ffprobe` are not on PATH, Gain dB now checks known install folders: winget Links, `C:\ffmpeg\bin`, `%ProgramFiles%\ffmpeg\bin` on Windows, and `/opt/homebrew/bin`, `/usr/local/bin` on macOS (apps started from Finder do not see your shell PATH). Both programs must come from the same place.
- **GUI: clear message when ffmpeg is missing.** Track/Album Analysis, and Track/Album Gain on files that still need analysis, now show one dialog with the folders that were searched and a link to the install guide, instead of failing file by file. Applying gain to already analyzed files, undo and tag check/delete still work without ffmpeg.

### Fixed
- On Linux/macOS, an answer piped to the clipping prompt (`echo y | ...`) could be swallowed by ffmpeg. ffmpeg/ffprobe no longer read your stdin.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI: dB within 0.1 dB, global gain min/max and applied steps identical, tags identical (peak within 1e-4 relative), and undo restores the audio bit for bit.

### Download
- `GainDB-0.6.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
