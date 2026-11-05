## Gain dB 1.0.0

Lossless MP3 volume analysis and adjustment, a Python re-implementation refactored from a reading of the mp3gain source (LGPL-2.1-or-later).

Analysis numbers, tags and CLI output are unchanged from 0.6.0. This release is about the GUI.

### New
- **Dark and light themes.** The GUI now uses the Graphite (dark) and Paper (light) themes. Choose System, Dark or Light under Options > Theme; the change applies at once and is remembered. The default follows your system.
- **Failed files stand out.** A file that could not be processed now shows its name in the warning color, with the error in its tooltip. Before, it looked the same as a file not yet analyzed.
- **Confirmation before Remove Tags.** Removing tags also removes the undo information, so the GUI now asks first.
- **Empty list hint and progress percent.** An empty list tells you to drag files or folders in, and the percentage is now shown next to the progress bar.

### Changed
- `clipping` colors follow the theme: possible clipping uses the accent color and definite clipping the warning color. The `?` and `clip` marks are unchanged.
- Backspace now removes selected rows from the list, like Delete (the files are not touched). This is the delete key on a Mac keyboard.
- Clear Analysis and Undo Gain Changes in the menus are enabled only when files are selected.
- Shortcut hints in tooltips use your system's notation (⌘ on macOS).
- PySide6 6.8 or newer is now required.

### Fixed
- **Album Gain and broken files.** One unreadable MP3 in an album made Album Gain skip every file and report nothing. The broken file is now marked as failed and the rest of the album is processed, as Album Analysis and the CLI already did.
- **Closing the window during a file change.** The window could force-stop a worker that was still writing a file after 10 seconds. It now waits for the write to finish.
- **Korean status bar.** Many status bar messages stayed in English in the Korean UI. They are now translated as whole sentences.
- **Log options: Browse did nothing.** The Browse buttons in Options > Logs did not open a file dialog. They now open the file dialog, stay available while a log is off, and choosing a file turns that log on.
- The application name was still "MP3 Gain" in places. It is now "Gain dB".

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI, including an album with a broken file.
- **macOS was checked on GitHub Actions macOS runners, not on a Mac in hand:** the GUI ran on the real platform through add, analyze, apply and undo, with screenshots of both themes, from source and from a PyInstaller build. File dialogs and dragging from Finder were not exercised. Please report anything that looks wrong.
- Windows was also checked by hand on a real machine.

### Download
- `GainDB-1.0.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
