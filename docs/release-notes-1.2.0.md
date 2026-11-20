## Gain dB 1.2.0

Analyze and even out MP3 loudness without re-encoding, from the command line or a GUI. Refactored into Python from the mp3gain source (LGPL-2.1-or-later).

Analysis numbers, tag formats and CLI output are unchanged from 1.1.2. This release adds four GUI languages and rewrites the README in six languages.

### New (GUI)
- **Six languages:** English, 한국어, 简体中文, 日本語, Español, Русский. Each language is shown by its own name in the Language menu, and choosing one changes the window at once, with no restart.
- **Start language.** A language you chose in the Language menu is used first. Otherwise Gain dB starts in your OS language if it is one of the six (Chinese only for Simplified Chinese regions; others start in English), and in English if not.
- **ffmpeg help in your language.** When ffmpeg is not found, the dialog links to the ffmpeg section of the README in the GUI language.
- dB, ReplayGain, mp3gain, APEv2, ID3v2, ffmpeg and ffprobe are not translated. Chinese and Japanese text uses your OS fonts; no fonts are bundled.

### Changed
- The README is rewritten in six languages, with a quick start, project status, how to contribute, and how to report a vulnerability privately.

### Verification
- CI on Windows, macOS and Ubuntu (Python 3.13). On macOS and Ubuntu the results are compared with the original mp3gain 1.6.2 CLI.
- Automated tests check every translation file (no untranslated text; placeholders, shortcut keys and kept terms match the English), the start language for each locale, and that the first window has no horizontal scroll bar in any of the six languages. Each language was checked in a screenshot on Windows. macOS was not checked by hand.

### Download
- `GainDB-1.2.0-windows.zip`: Windows build (onedir). Unzip and run `GainDB.exe`; keep the whole folder together. ffmpeg is not included, see [Installing ffmpeg](https://github.com/metapbl/GainDB/blob/main/README.md#installing-ffmpeg).
- macOS/Linux: run from source (`pip install -r requirements.txt`, then `python -m gui` or `python gaindb_cli.py`).

License texts (LGPL-2.1-or-later, NOTICE, third-party and Qt LGPLv3) are in the `licenses/` folder of the zip.
