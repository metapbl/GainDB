[English](README.md) | 한국어

# Gain dB

MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구입니다.
MP3 프레임의 `global_gain` 필드를 직접 조정해 음량을 바꾸므로 재인코딩이
없습니다. mp3gain 의 결과(동작·태그 포맷·출력·수치)와 호환되도록 일치시킨
독립 재구현입니다.

![License](https://img.shields.io/badge/license-Apache--2.0-blue)
![Python](https://img.shields.io/badge/python-3.13%2B-blue)

## 기능

- **무손실 음량 조정.** MP3 각 프레임의 사이드 정보에는 8비트 `global_gain`
  필드가 있습니다. 이를 N 스텝 조정하면 디코딩된 샘플이 `2^(N/4)`(약 1.5 dB/
  스텝)로 스케일되며, 재인코딩이 없어 완전 무손실입니다.
- **인지 음량 분석.** PCM 으로 디코딩한 뒤 ReplayGain 알고리즘(equal-loudness
  필터 + RMS + 통계)으로 목표 음량(기본 89 dB)에 맞추는 데 필요한 게인을
  계산합니다.
- **Track / Album 모드.** Track 게인은 파일마다 음량을 고르게 맞추고, Album
  게인은 곡 간 상대 음량을 유지한 채 하나의 공통 조정을 적용합니다.
- **태그 처리.** APEv2(기본) 또는 ID3v2 태그의 ReplayGain·mp3gain 필드를
  읽기·쓰기·갱신·제거하며 undo 정보도 다룹니다.
- **CLI 와 GUI.** mp3gain 호환 옵션 체계를 갖춘 명령줄 도구와, 크로스플랫폼
  PySide6 GUI(Windows·macOS)를 제공합니다.

## 범위: MP3 전용

Gain dB 는 **설계상 MP3 전용**입니다. 무손실 게인 기법은 MP3 비트스트림
고유의 `global_gain` 필드에 의존하며, 다른 포맷에는 대응 구조가 없어
원리적으로 적용할 수 없습니다. 타 포맷은 범위 밖입니다.

## 요구 사항

- **Python 3.13 이상.**
- **PATH 에 ffmpeg 와 ffprobe.** Gain dB 는 ffmpeg 를 동봉하지 않고 PCM
  디코딩을 위해 외부 프로세스로 호출합니다. 사용자가 직접 설치하세요(아래 참조).
- **파이썬 패키지:** numpy, scipy(분석)와 PySide6(GUI). `requirements.txt`
  로 설치합니다.

### ffmpeg 설치

플랫폼에 맞는 빌드를 내려받아 `ffmpeg` 와 `ffprobe` 가 모두 PATH 에서
찾아지도록 설정하세요:

- **Windows:** https://www.gyan.dev/ffmpeg/builds/ ("release essentials" 빌드)
- **macOS:** https://evermeet.cx/ffmpeg/
- **Linux:** https://johnvansickle.com/ffmpeg/ (static builds)

## 설치

```
git clone <저장소-URL> GaindB
cd GaindB
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# macOS / Linux:
# source .venv/bin/activate
pip install -r requirements.txt
```

## 사용법

### 명령줄

```
python gaindb_cli.py [options] <infile> [<infile 2> ...]
```

자주 쓰는 옵션(mp3gain 호환):

- `-r` 모든 파일이 같은 음량이 되도록 Track 게인 적용
- `-a` 모든 파일에 하나의 공통 Album 게인 적용
- `-k` 클리핑이 없도록 Track/Album 게인을 필요한 만큼 낮춤
- `-s c` 저장된 태그 정보만 보고
- `-s d` 저장된 태그 정보만 삭제
- `-s i` ID3v2 태그에 게인 정보 저장(기본은 APE)
- `-u` 저장된 태그 정보로 이전 변경 되돌리기
- `-o` 탭 구분 데이터베이스 형식으로 출력

전체 옵션은 `python gaindb_cli.py -h`, `-w` wrap 옵션 설명은
`python gaindb_cli.py -? wrap` 로 확인하세요.

예시:

```
# 파일을 바꾸지 않고 Track 게인만 제안
python gaindb_cli.py song.mp3

# 단일 파일에 Track 게인 적용
python gaindb_cli.py -r song.mp3

# 폴더의 파일들에 클리핑을 피하며 Album 게인 적용
python gaindb_cli.py -a -k album/*.mp3

# 이전 변경 되돌리기
python gaindb_cli.py -u song.mp3
```

### 그래픽 인터페이스

```
python -m gui
```

GUI 는 파일/폴더 목록, Track/Album 분석·게인, 우클릭 메뉴, 취소, 컬럼폭·
정렬 저장, 로그, 트레이 아이콘, 영어/한국어 전환을 제공합니다.

## mp3gain 과의 관계

Gain dB 는 **독립 재구현**입니다. 결과가 호환되도록 mp3gain 의 관찰된 동작,
명령줄 옵션 체계, 파일·태그 포맷을 재현하지만, mp3gain 의 원본 소스 코드를
포함하거나 그로부터 파생하지 **않습니다.** 음량 분석은 공개된 ReplayGain
사양을 따르며, 필터 계수 값은 여러 독립 구현이 공유하는 공개 표준 수치입니다.
자세한 내용은 `NOTICE` 파일을 참고하세요.

## 라이선스

Gain dB 는 **Apache License, Version 2.0** 으로 배포됩니다. 전문은 `LICENSE`
파일, 고지·의존성 안내는 `NOTICE` 파일을 참고하세요.

의존성 라이선스: numpy·scipy 는 BSD-3-Clause, PySide6(Qt for Python)는
LGPLv3 입니다. ffmpeg 는 동봉하지 않고 PATH 에서 호출합니다. 만약 ffmpeg
빌드를 이 소프트웨어와 함께 배포한다면 LGPL 빌드를 쓰고 해당 라이선스를
준수하세요(GPL 빌드는 이 프로젝트의 라이선스와 호환되지 않습니다).