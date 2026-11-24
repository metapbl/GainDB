## Gain dB 1.3.0

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

Analysis numbers and tag formats are unchanged from 1.2.0, except for the CLI `-x` fix below. This release adds the remaining gain features of the original mp3gain GUI.

### New (GUI)
- **Modify > Apply Constant Gain... (Ctrl+O).** Changes the selected files (or all files) by a fixed number of steps, from -8 to +8 (1.5 dB per step), without analysis. As in the original GUI, the change can be limited to the left or right channel. Undo works as usual.
- **Options > Enable "Maximizing" features.** Off by default and remembered. When turned on, a short note explains that maximizing is not volume normalizing, and these appear:
  - **Analysis > Max No-clip analysis (Ctrl+M):** finds only the max amplitude of the files, without loudness analysis.
  - **Max Noclip Gain column:** the largest change, in dB, that does not clip. It is red when the file already clips.
  - **Modify > Apply Max No-clip Gain for Each file (Ctrl+X)** and **for Album (Ctrl+L):** raise each file, or each album by the smallest value among its files, as far as it can go without clipping.

### Changed
- **Track Gain skips files whose stored value is already at the target**, as the original GUI does. Files that were only analyzed (not yet tagged) are still processed so that their tags get written.
- The new column changes the column layout, so saved column widths and the saved sort column are reset once to their defaults.

### Fixed
- **CLI `-x` wrote the wrong tags.** It left out the track max amplitude and min/max `global_gain`, and wrote an album gain of 0 dB. Like mp3gain, `-x` now writes only the max amplitude and min/max `global_gain` (for the tracks and, with several files, the album) and leaves the gain values alone. The printed values were already correct.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI, now including `-x`, `-g` and `-l` and the tags they leave.
- The new GUI features are covered by automated tests on copies of test files: Constant Gain gives the same file as CLI `-g` / `-l`, and after Max No-clip gain no file can be raised further without clipping. The new screens were checked in Korean on Windows. macOS was not checked by hand.

### Download
- `GainDB-1.3.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
