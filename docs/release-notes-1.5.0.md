## Gain dB 1.5.0

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

A smaller download. Gain dB no longer needs SciPy, so it is left out of the Windows build. Analysis numbers, tag formats and CLI output are unchanged.

### Changed
- **SciPy is no longer a dependency.** The ReplayGain loudness filter now runs on numpy alone. The Windows zip shrinks from 96.5 MB to {zip size} MB, and the unzipped folder from 225 MB to {folder size} MB.
- Analysis is about as fast as before. On a 4-minute test track it was 6–13% faster on the test PC.
- To run from source you only need numpy and PySide6 (`requirements.txt`). SciPy is now used only to create test files and to check the new filter against the old one (`requirements-dev.txt`).

### Verification
- Track and album gain, peak and the applied gain steps are the same as in 1.4.1 for every test file. New automated tests compare the new filter with the SciPy filter, and check that streaming analysis gives exactly the same result however the audio is split into chunks.
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.

### Download
- `GainDB-1.5.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
