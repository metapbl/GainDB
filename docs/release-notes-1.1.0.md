## Gain dB 1.1.0

Lossless MP3 volume analysis and adjustment, a Python re-implementation refactored from a reading of the mp3gain source (LGPL-2.1-or-later).

Analysis numbers and tag formats are unchanged from 1.0.0. This release adds three options from the original mp3gain GUI and fixes `-p` in the CLI.

### New (GUI, Options menu)
All three are off by default and remembered.
- **Preserve file date/time.** Track Gain, Album Gain, Undo and Remove Tags keep each file's modified time.
- **Don't clip when doing Track Gain.** Track Gain is lowered to the largest change that does not clip. As in the original GUI, a file that already clips is lowered even when its suggested change is 0. Album Gain is not affected.
- **Tags > Re-calculate (do not read tags).** Added files are not read for stored values, so Track Gain analyzes them instead.

### Fixed
- **CLI `-p` did not keep the file time when gain was applied.** The time was saved only around the tag write, after the gain had already changed the file. `-r`, `-a`, `-g`, `-l`, `-u` and `-s s` with `-p` now keep the original time, as mp3gain does.

### Changed
- The theme is updated to Graphite/Paper 1.4.3: outlined default buttons, a 2px keyboard focus ring, buttons take focus by Tab only (not by click), and a focused button outside dialogs can be pressed with Enter. Light-theme grooves and borders are easier to see.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI, now including `-p` file times after `-r`, `-u`, `-a` and `-g`.
- The new GUI options are covered by automated tests on copies of test files. macOS was not checked by hand.

### Download
- `GainDB-1.1.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
