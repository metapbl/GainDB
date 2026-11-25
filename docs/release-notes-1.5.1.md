## Gain dB 1.5.1

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

A notice fix for 1.5.0. Analysis numbers, tag formats and CLI output are unchanged.

### Fixed
- The About window and the NOTICE file still listed SciPy as a third-party component. SciPy is not part of Gain dB since 1.5.0, so both now list NumPy only.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- The About window of the Windows build was checked by hand.

### Download
- `GainDB-1.5.1-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
