<p align="center">
  <strong>Language:</strong>
  <a href="README.md">English</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.zh-CN.md">简体中文</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.ru.md">Русский</a>
</p>

# Gain dB

<p align="center">
  <a href="https://github.com/metapbl/GainDB/releases"><img alt="Release" src="https://img.shields.io/github/v/release/metapbl/GainDB?style=flat-square"></a>
  <a href="LICENSE"><img alt="License: LGPL-2.1-or-later" src="https://img.shields.io/badge/license-LGPL--2.1--or--later-blue?style=flat-square"></a>
  <a href="#requirements"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="#installation"><img alt="OS: Windows, macOS, Linux" src="https://img.shields.io/badge/os-Windows_%7C_macOS_%7C_Linux-lightgrey?style=flat-square"></a>
</p>

Lossless MP3 volume analysis and adjustment with a CLI and GUI, result-compatible with mp3gain.

## What it does

Gain dB measures how loud your MP3 files sound and evens them out
**without re-encoding**, so there is no quality loss. It was refactored into
Python from a reading of the mp3gain source and gives the same results as
mp3gain: the same dB values, gain steps and tags.

- **Lossless gain change.** Each MP3 frame has an 8-bit `global_gain` field.
  Changing it by N steps scales the sound by `2^(N/4)` (about 1.5 dB per
  step) without touching the audio data, and the change can be undone.
- **Loudness analysis.** The audio is decoded with ffmpeg and measured with
  the ReplayGain algorithm to find the change needed to reach a target
  loudness (89 dB by default).
- **Track and Album modes.** Track gain evens out each file. Album gain
  applies one shared change so the loudness differences between tracks stay
  as they are.
- **Tags.** Reads, writes and removes ReplayGain and mp3gain tags in APEv2
  (default) or ID3v2, including the undo information.
- **CLI and GUI.** A command-line tool with the mp3gain options, and a
  PySide6 GUI for Windows and macOS with dark and light themes, six
  languages (English, 한국어, 简体中文, 日本語, Español, Русский) and the
  options of the original mp3gain GUI.

Gain dB works on **MP3 files only**, by design: the lossless technique
depends on the MP3 `global_gain` field, which other formats do not have.

## Requirements

- **ffmpeg and ffprobe** — needed for analysis. They are not bundled; install
  them yourself (see below).
- **To run from source:** Python 3.13 or newer. The packages (numpy, scipy,
  PySide6) are installed from `requirements.txt`.

### Installing ffmpeg

Download a build for your system and make sure both `ffmpeg` and `ffprobe`
are on your PATH:

- **Windows:** `winget install Gyan.FFmpeg`, or the "release essentials"
  build from https://www.gyan.dev/ffmpeg/builds/
- **macOS:** `brew install ffmpeg`, or a build from https://evermeet.cx/ffmpeg/
- **Linux:** your package manager (for example `sudo apt install ffmpeg`), or
  a static build from https://johnvansickle.com/ffmpeg/

Gain dB looks on your PATH first. If they are not there, it also checks
these folders in order, using a folder only if it holds both programs:

- **Windows:** `%LOCALAPPDATA%\Microsoft\WinGet\Links` (winget),
  `C:\ffmpeg\bin`, `%ProgramFiles%\ffmpeg\bin`
- **macOS:** `/opt/homebrew/bin`, `/usr/local/bin` (Homebrew; this covers
  apps started from Finder, which do not see your shell PATH)

## Installation

**Windows app:** download `GainDB-<version>-windows.zip` from
[Releases](https://github.com/metapbl/GainDB/releases), unzip it and run
`GainDB.exe` in the `GainDB` folder. No Python is needed.

**From source (Windows, macOS, Linux):**

```
git clone https://github.com/metapbl/GainDB.git
cd GainDB
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

This creates a virtual environment in `.venv` and installs the packages
into it.

## Quick start

Open the GUI (from source: `python -m gui`), add files or a folder, then
choose **Analysis > Album Analysis**, then **Modify > Album Gain**. The
analysis fills in the dB columns; the gain step changes the files and stores undo tags.

On the command line, analysis alone does not change the file:

```
python gaindb_cli.py song.mp3
```

```
song.mp3
Recommended "Track" dB change: -7.880000
Recommended "Track" mp3 gain change: -5
Max PCM sample at current gain: 30976.785156
Max mp3 global gain field: 210
Min mp3 global gain field: 158
```

The numbers depend on your file. A gain change of `-5` means the file would
be lowered by 5 steps (about 7.5 dB).

## Usage

### Command line

```
python gaindb_cli.py [options] <infile> [<infile 2> ...]
```

Common options (the same as mp3gain):

- `-r` apply Track gain so every file ends up at equal loudness
- `-a` apply one shared Album gain to every file
- `-k` lower the Track/Album gain as needed to avoid clipping
- `-s c` only show the stored tag info
- `-s d` only delete the stored tag info
- `-s i` store gain info in an ID3v2 tag (APEv2 is the default)
- `-u` undo previous changes, using the stored tag info
- `-o` print a tab-delimited, database-friendly listing

`python gaindb_cli.py -h` prints every option, and
`python gaindb_cli.py -? wrap` explains the `-w` wrap option.

```
# Apply Track gain to one file
python gaindb_cli.py -r song.mp3

# Apply Album gain to a folder's files, avoiding clipping
python gaindb_cli.py -a -k album/*.mp3

# Undo previous changes
python gaindb_cli.py -u song.mp3
```

Each command prints what it changed, file by file. Make a copy of your files
before the first run if you are unsure.

### Graphical interface

```
python -m gui
```

This opens the main window. It has file and folder lists, Track/Album
analysis and gain, a right-click menu, cancel, a log window and a tray icon.
The Language menu and Options > Theme change the screen at once. The
Options menu can keep file dates, avoid clipping in Track Gain, and always
recalculate instead of reading stored tags.

## How this project relates to mp3gain

Gain dB is a Python refactoring of the mp3gain source. It keeps the
behaviour, the command-line options and the file and tag formats of mp3gain
so that results are compatible. The tag handling and lossless gain-writing
modules are adapted from the mp3gain C sources, which are licensed under the
GNU LGPL v2.1 or later, and Gain dB as a whole uses the same license.
Loudness analysis follows the public ReplayGain specification; its filter
coefficients are standard numbers shared across independent implementations.
See [NOTICE](NOTICE) for details.

## Project status

- Version 1.x, in regular use. The command-line options follow mp3gain and
  are not expected to change.
- Every push runs the test suite on Windows, macOS and Ubuntu. On macOS and
  Ubuntu it also compares dB values, gain steps and tags with mp3gain.
- The GUI is checked on Windows and on a macOS runner. Release builds are for
  Windows only; on macOS and Linux, run from source. The GUI has not been
  tried on Linux.

## Help and contributing

- Questions and bug reports: [GitHub Issues](https://github.com/metapbl/GainDB/issues).
- Pull requests are welcome. For larger changes, open an issue first to
  discuss them. Contributions are accepted under LGPL-2.1-or-later.
- Before sending a pull request, run the full test suite (it needs ffmpeg):

```
python tests/_gen_fixtures.py
python -m unittest discover -s tests
```

The first command creates test MP3 files; the second runs every test.

## Security

Please report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/metapbl/GainDB/security/advisories/new),
not in a public issue.

## Credits

Gain dB is based on [mp3gain](https://sourceforge.net/projects/mp3gain/) by
Glen Sawyer, with ReplayGain analysis by David Robinson and Glen Sawyer, and
improvements by Frank Klemm and Marcel Mueller. It uses
[numpy](https://numpy.org/), [SciPy](https://scipy.org/),
[PySide6](https://doc.qt.io/qtforpython-6/) and, as an external program,
[ffmpeg](https://ffmpeg.org/).

## License

[LGPL-2.1-or-later](LICENSE). See [NOTICE](NOTICE) for the mp3gain copyright
notices and [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES) for dependencies.
numpy and SciPy are BSD-3-Clause; PySide6 (Qt for Python) is LGPLv3. ffmpeg
is not bundled; if you distribute an ffmpeg build with this software, use an
LGPL build and follow its license terms.
