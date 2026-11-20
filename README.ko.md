<p align="center">
  <strong>Language:</strong>
  <a href="README.md">English</a> |
  <a href="README.ko.md">한국어</a> |
  <a href="README.zh-CN.md">简体中文</a> |
  <a href="README.ja.md">日本語</a> |
  <a href="README.es.md">Español</a> |
  <a href="README.ru.md">Русский</a>
</p>

> 이 문서는 영어판을 AI로 번역한 것입니다. 내용이 다르면 영어판을 따릅니다.

# Gain dB

<p align="center">
  <a href="https://github.com/metapbl/GainDB/releases"><img alt="Release" src="https://img.shields.io/github/v/release/metapbl/GainDB?style=flat-square"></a>
  <a href="LICENSE"><img alt="License: LGPL-2.1-or-later" src="https://img.shields.io/badge/license-LGPL--2.1--or--later-blue?style=flat-square"></a>
  <a href="#요구-사항"><img alt="Python 3.13+" src="https://img.shields.io/badge/python-3.13%2B-3776AB?style=flat-square&logo=python&logoColor=white"></a>
  <a href="#설치"><img alt="OS: Windows, macOS, Linux" src="https://img.shields.io/badge/os-Windows_%7C_macOS_%7C_Linux-lightgrey?style=flat-square"></a>
</p>

CLI와 GUI로 MP3 음량을 무손실 분석·조정하며, 결과가 mp3gain과 같습니다.

## 기능

Gain dB는 MP3 파일이 얼마나 크게 들리는지 측정하고 **재인코딩 없이** 고르게
맞춥니다. 그래서 음질 손실이 없습니다. mp3gain 소스를 읽고 Python으로
리팩토링한 프로그램이며, mp3gain과 같은 결과(dB 값·게인 단계·태그)를 냅니다.

- **무손실 게인 변경.** MP3 프레임마다 8비트 `global_gain` 필드가 있습니다.
  이 값을 N단계 바꾸면 소리가 `2^(N/4)`배(단계당 약 1.5 dB) 커지거나 작아지고,
  오디오 데이터는 건드리지 않으며 되돌릴 수 있습니다.
- **음량 분석.** ffmpeg로 디코딩한 오디오를 ReplayGain 알고리즘으로 측정해
  목표 음량(기본 89 dB)에 맞추는 데 필요한 변경량을 구합니다.
- **Track·Album 모드.** Track 게인은 파일마다 고르게 맞춥니다. Album 게인은
  모든 파일에 같은 변경을 적용해 트랙 사이의 음량 차이를 그대로 둡니다.
- **태그.** APEv2(기본) 또는 ID3v2에 ReplayGain·mp3gain 태그를 읽고 쓰고
  지우며, 되돌리기 정보도 저장합니다.
- **CLI와 GUI.** mp3gain 옵션을 그대로 쓰는 명령줄 도구와, Windows·macOS용
  PySide6 GUI를 제공합니다. GUI는 다크·라이트 테마, 6개 언어(English, 한국어,
  简体中文, 日本語, Español, Русский), 원본 mp3gain GUI의 옵션을 지원합니다.

Gain dB는 설계상 **MP3 파일만** 다룹니다. 무손실 방식이 MP3의 `global_gain`
필드에 기대는데, 다른 포맷에는 이 필드가 없습니다.

## 요구 사항

- **ffmpeg와 ffprobe** — 분석에 필요합니다. 함께 배포하지 않으므로 직접
  설치하세요(아래 참고).
- **소스에서 실행할 때:** Python 3.13 이상. 패키지(numpy, scipy, PySide6)는
  `requirements.txt`로 설치합니다.

### ffmpeg 설치

사용하는 시스템용 빌드를 받고 `ffmpeg`와 `ffprobe`가 둘 다 PATH에 있게
하세요.

- **Windows:** `winget install Gyan.FFmpeg`, 또는
  https://www.gyan.dev/ffmpeg/builds/ 의 "release essentials" 빌드
- **macOS:** `brew install ffmpeg`, 또는 https://evermeet.cx/ffmpeg/ 의 빌드
- **Linux:** 패키지 관리자(예: `sudo apt install ffmpeg`), 또는
  https://johnvansickle.com/ffmpeg/ 의 정적 빌드

Gain dB는 먼저 PATH를 찾습니다. 거기 없으면 아래 폴더를 차례로 확인하고,
두 프로그램이 모두 있는 폴더만 씁니다.

- **Windows:** `%LOCALAPPDATA%\Microsoft\WinGet\Links` (winget),
  `C:\ffmpeg\bin`, `%ProgramFiles%\ffmpeg\bin`
- **macOS:** `/opt/homebrew/bin`, `/usr/local/bin` (Homebrew. Finder에서 실행한
  앱은 셸 PATH를 보지 못하므로 이 경우도 찾습니다)

## 설치

**Windows 앱:** [Releases](https://github.com/metapbl/GainDB/releases)에서
`GainDB-<버전>-windows.zip`을 받아 압축을 풀고 `GainDB` 폴더의 `GainDB.exe`를
실행합니다. Python은 필요 없습니다.

**소스에서 (Windows, macOS, Linux):**

```
git clone https://github.com/metapbl/GainDB.git
cd GainDB
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -r requirements.txt
```

`.venv`에 가상 환경을 만들고 그 안에 패키지를 설치합니다.

## 빠른 시작

GUI를 열고(소스에서는 `python -m gui`) 파일이나 폴더를 추가한 다음
**분석 > 앨범 분석**, **수정 > 앨범 게인** 순서로 고릅니다. 분석이 dB 컬럼을
채우고, 게인 단계가 파일을 바꾸며 되돌리기 태그를 저장합니다.

명령줄에서는 분석만 하면 파일이 바뀌지 않습니다.

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

숫자는 파일마다 다릅니다. 게인 변경 `-5`는 파일을 5단계(약 7.5 dB) 낮춘다는
뜻입니다.

## 사용법

### 명령줄

```
python gaindb_cli.py [options] <infile> [<infile 2> ...]
```

자주 쓰는 옵션(mp3gain과 같음):

- `-r` 모든 파일이 같은 음량이 되도록 Track 게인 적용
- `-a` 모든 파일에 같은 Album 게인 하나를 적용
- `-k` 클리핑이 나지 않도록 Track/Album 게인을 필요한 만큼 낮춤
- `-s c` 저장된 태그 정보만 표시
- `-s d` 저장된 태그 정보만 삭제
- `-s i` 게인 정보를 ID3v2 태그에 저장(기본은 APEv2)
- `-u` 저장된 태그 정보로 이전 변경을 되돌림
- `-o` 탭으로 구분한, 데이터베이스에 넣기 좋은 목록 출력

`python gaindb_cli.py -h`는 모든 옵션을 보여 주고,
`python gaindb_cli.py -? wrap`은 `-w` wrap 옵션을 설명합니다.

```
# Apply Track gain to one file
python gaindb_cli.py -r song.mp3

# Apply Album gain to a folder's files, avoiding clipping
python gaindb_cli.py -a -k album/*.mp3

# Undo previous changes
python gaindb_cli.py -u song.mp3
```

각 명령은 바꾼 내용을 파일별로 출력합니다. 처음 실행할 때 확신이 없으면 파일을
먼저 복사해 두세요.

### 그래픽 인터페이스

```
python -m gui
```

메인 창이 열립니다. 파일·폴더 목록, Track/Album 분석과 게인, 오른쪽 클릭 메뉴,
취소, 로그 창, 트레이 아이콘이 있습니다. 언어 메뉴와 옵션 > 테마는 화면을
바로 바꿉니다. 옵션 메뉴에서 파일 날짜 유지, Track 게인의 클리핑 방지, 저장된
태그를 읽지 않고 항상 다시 계산하기를 고를 수 있습니다.

## mp3gain과의 관계

Gain dB는 mp3gain 소스를 Python으로 리팩토링한 프로그램입니다. 결과가
호환되도록 mp3gain의 동작, 명령줄 옵션, 파일·태그 형식을 그대로 따릅니다. 태그
처리와 무손실 게인 쓰기 모듈은 GNU LGPL v2.1 이상으로 배포되는 mp3gain C
소스를 개작한 것이고, Gain dB 전체도 같은 라이선스를 씁니다. 음량 분석은 공개된
ReplayGain 사양을 따르며, 필터 계수는 여러 독립 구현이 공유하는 공개 표준
수치입니다. 자세한 내용은 [NOTICE](NOTICE)를 보세요.

## 프로젝트 상태

- 버전 1.x, 실제로 쓰고 있습니다. 명령줄 옵션은 mp3gain을 따르며 바뀔 예정이
  없습니다.
- push마다 Windows·macOS·Ubuntu에서 테스트를 돌립니다. macOS와 Ubuntu에서는
  dB 값·게인 단계·태그를 mp3gain과 대조합니다.
- GUI는 Windows와 macOS 러너에서 확인합니다. 릴리스 빌드는 Windows용뿐이고,
  macOS·Linux에서는 소스로 실행합니다. Linux GUI는 시험하지 않았습니다.

## 도움말과 기여

- 질문과 버그 신고: [GitHub Issues](https://github.com/metapbl/GainDB/issues).
- Pull request를 환영합니다. 큰 변경은 먼저 이슈를 열어 논의해 주세요.
  기여분은 LGPL-2.1-or-later로 받습니다.
- Pull request를 보내기 전에 전체 테스트를 돌려 주세요(ffmpeg 필요).

```
python tests/_gen_fixtures.py
python -m unittest discover -s tests
```

첫 명령은 테스트용 MP3 파일을 만들고, 두 번째 명령은 모든 테스트를 돌립니다.

## 보안

취약점은 공개 이슈가 아니라
[GitHub 비공개 취약점 신고](https://github.com/metapbl/GainDB/security/advisories/new)로
알려 주세요.

## 감사의 말

Gain dB는 Glen Sawyer의 [mp3gain](https://sourceforge.net/projects/mp3gain/)을
바탕으로 합니다. ReplayGain 분석은 David Robinson과 Glen Sawyer가 만들고 Frank
Klemm과 Marcel Mueller가 개선했습니다. [numpy](https://numpy.org/),
[SciPy](https://scipy.org/), [PySide6](https://doc.qt.io/qtforpython-6/)를 쓰고,
외부 프로그램으로 [ffmpeg](https://ffmpeg.org/)를 씁니다.

## 라이선스

[LGPL-2.1-or-later](LICENSE). mp3gain 저작권 고지는 [NOTICE](NOTICE)에,
의존성 라이선스는 [THIRD_PARTY_LICENSES](THIRD_PARTY_LICENSES)에 있습니다.
numpy와 SciPy는 BSD-3-Clause, PySide6(Qt for Python)는 LGPLv3입니다. ffmpeg는
함께 배포하지 않습니다. 이 소프트웨어와 함께 ffmpeg 빌드를 배포한다면 LGPL
빌드를 쓰고 그 라이선스 조건을 따르세요.
