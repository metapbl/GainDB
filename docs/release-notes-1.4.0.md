## Gain dB 1.4.0

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

A GUI release. Analysis numbers, tag formats and CLI output are unchanged from 1.3.1.

### Changed (GUI)
- **A narrower main window.** Column headers now use two lines where they can (for example "Track / Gain"), and the number columns are only as wide as their header or values need. Path\File starts at 300 px; long paths are shortened in the middle as before. The first window is 20–30% narrower in all six languages (for example 1090 → 825 px in English and 1288 → 920 px in Spanish). Headers break between words, before a parenthesis, where Japanese script changes, or every two Chinese characters, never inside a Korean or Latin word.
- Because of the new layout, the saved window size and column widths are reset once when 1.4.0 first starts. Other settings are kept.
- Turning on Options > Enable "Maximizing" features now widens the window for the new column (within the screen, unless the window is maximized), so no horizontal scroll bar appears.

### New (GUI)
- **File > Select All Files (Ctrl+A), Select No Files (Ctrl+N) and Invert selection (Ctrl+V)**, as in the original mp3gain GUI.
- **Language > System default.** Forgets the language you picked and uses your OS language again, at once. It is checked when you have not picked a language.

### Fixed
- **Column headers were cut off after changing the language.** Column widths were fitted to the headers only on the first start, so switching language, or starting with widths saved in another language, could cut headers off. Columns narrower than their header now grow to fit; columns you made wider stay as they are.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- Automated tests check the header line-break rule for each script, that the first window is at least 20% narrower than in 1.3.1 with no horizontal scroll bar and no cut-off header in any of the six languages, header widths after a language change and after a restart, the selection items, and System default. The new layout was checked in screenshots in all six languages on Windows. macOS was not checked by hand.

### Download
- `GainDB-1.4.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
