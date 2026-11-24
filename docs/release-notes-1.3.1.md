## Gain dB 1.3.1

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

A bug-fix release for the GUI. Analysis numbers, tag formats and CLI output are unchanged from 1.3.0.

### Fixed
- **Applying Max No-clip Gain twice could make files clip.** After any gain change (Track Gain, Album Gain, Constant Gain, Max No-clip or Undo), the window kept the old max amplitude for the Max Noclip Gain column and for the next Max No-clip apply, so a second apply raised the files again. The amplitude now moves with every change, as in the original mp3gain GUI. The same fix keeps Track Gain from writing an old max amplitude to the tags after an Undo.
- Rows that only had a Max No-clip analysis now also update their amplitude after a gain change.

### Changed
- **Max No-clip analysis skips files whose max amplitude is already known**, as the original GUI does. If every file is known, it reports that there are no files to analyze.
- The Max Noclip Gain cell is blank for a max amplitude of 1,000,000 or more (a damaged file), as in the original GUI.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- New automated tests: a second Max No-clip apply changes nothing, the shown amplitude after a gain change matches a fresh analysis, and a three-file album ends with no file able to go higher without clipping. macOS was not checked by hand.

### Download
- `GainDB-1.3.1-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
