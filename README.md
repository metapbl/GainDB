English | [한국어](README.ko.md)

# Gain dB

Lossless MP3 volume analysis and adjustment. Gain dB analyzes and changes
the loudness of MP3 files **without re-encoding**, by editing the MP3
`global_gain` field directly. It is a Python re-implementation refactored
from a reading of the mp3gain source (some modules are adaptations of the
original; LGPL retained), and it reproduces the results (behaviour, tag
formats, output, numbers) of mp3gain while remaining compatible with it.

![License](https://img.shields.io/badge/license-LGPL--2.1--or--later-blue)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)

## What it does

- **Lossless gain change.** Each MP3 frame carries an 8-bit `global_gain`
  field in its side information. Adjusting it by N steps scales the decoded
  samples by `2^(N/4)` (about 1.5 dB per step) with no re-encoding, so the
  change is fully lossless.
- **Perceptual loudness analysis.** Audio is decoded to PCM and measured
  with the ReplayGain algorithm (equal-loudness filter + RMS + statistics)
  to compute the gain needed to reach a target loudness (89 dB by default).
- **Track and Album modes.** Track gain equalizes each file; Album gain
  applies one shared change so relative loudness between tracks is kept.
- **Tag handling.** Reads, writes, updates, and removes ReplayGain and
  mp3gain tag fields in APEv2 (default) or ID3v2 tags, including undo info.
- **CLI and GUI.** A command-line tool with an mp3gain-compatible option
  scheme, plus a cross-platform PySide6 GUI (Windows and macOS).

## Scope: MP3 only

Gain dB is **MP3-only by design.** The lossless gain technique relies on
the MP3 `global_gain` field, which is specific to the MP3 bitstream and has
no equivalent in other formats. Other formats are out of scope.

## Requirements

- **Python 3.13 or newer.**
- **ffmpeg and ffprobe.** Gain dB does not bundle ffmpeg; it
  calls it as an external process for PCM decoding. Install it yourself
  (see below).
- **Python packages:** numpy, scipy (analysis) and PySide6 (GUI). These are
  installed via `requirements.txt`.

### Installing ffmpeg

Download a build for your platform and make sure both `ffmpeg` and
`ffprobe` are reachable on your PATH:

- **Windows:** https://www.gyan.dev/ffmpeg/builds/ (the "release
  essentials" build)
- **macOS:** https://evermeet.cx/ffmpeg/
- **Linux:** https://johnvansickle.com/ffmpeg/ (static builds)

Gain dB looks on your PATH first. If they are not there, it also checks
these folders in order, using a folder only if it holds both programs:

- **Windows:** `%LOCALAPPDATA%\Microsoft\WinGet\Links` (winget),
  `C:\ffmpeg\bin`, `%ProgramFiles%\ffmpeg\bin`
- **macOS:** `/opt/homebrew/bin`, `/usr/local/bin` (Homebrew; covers apps
  started from Finder, which do not see your shell PATH)

## Installation

```
git clone <your-repo-url> GaindB
cd GaindB
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

## Usage

### Command line

```
python gaindb_cli.py [options] <infile> [<infile 2> ...]
```

Common options (mp3gain-compatible):

- `-r` apply Track gain so every file ends up at equal loudness
- `-a` apply one shared Album gain to every file
- `-k` lower the Track/Album gain as needed to avoid clipping
- `-s c` only report the stored tag info
- `-s d` only delete the stored tag info
- `-s i` store gain info in an ID3v2 tag (APE is the default)
- `-u` undo previous changes, using the stored tag info
- `-o` print a tab-delimited, database-friendly listing

Run `python gaindb_cli.py -h` for the full option list, and
`python gaindb_cli.py -? wrap` for an explanation of the `-w` wrap option.

Examples:

```
# Suggest a Track gain without changing the file
python gaindb_cli.py song.mp3

# Apply Track gain to a single file
python gaindb_cli.py -r song.mp3

# Apply Album gain across a folder's files, avoiding clipping
python gaindb_cli.py -a -k album/*.mp3

# Undo previous changes
python gaindb_cli.py -u song.mp3
```

### Graphical interface

```
python -m gui
```

The GUI provides file/folder lists, Track/Album analysis and gain, a
right-click menu, cancellation, column persistence, logging, a tray icon,
and English/Korean localization.

## How this project relates to mp3gain

Gain dB is a **Python re-implementation of mp3gain.** It reproduces the
observable behaviour, the command-line option scheme, and the file and tag
formats of mp3gain so that results are compatible. Portions of the code
(in particular the tag handling and the lossless gain-writing modules) are
based on, and adapted from, the mp3gain C sources, which are licensed
under the GNU LGPL v2.1 or later; Gain dB as a whole is distributed under
the same license. Loudness analysis follows the publicly documented
ReplayGain specification; the filter coefficient values are public
standard numbers shared across independent implementations. See the
`NOTICE` file for details.

## License

Gain dB is licensed under the **GNU Lesser General Public License,
version 2.1 or (at your option) any later version (LGPL-2.1-or-later)**.
See the `LICENSE` file for the full text and `NOTICE` for attribution
(including the mp3gain copyright notices) and dependency notices.

Dependency licenses: numpy and scipy are BSD-3-Clause; PySide6 (Qt for
Python) is LGPLv3. ffmpeg is not bundled and is found on your PATH or in a known install folder; if
you choose to distribute an ffmpeg build alongside this software, use an
LGPL build and follow its license terms.
