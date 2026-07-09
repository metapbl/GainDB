# Gain dB — Claude 컨텍스트 파일

> 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하는 컨텍스트 파일.
> 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고, 그 세션 단계에 필요한 C 소스를 함께 붙여넣는다 (자세한 방법은 "12. 새 세션 시작 방법" 참조).

---

## 1. 프로젝트 정체성

- **표시 이름**: Gain dB
- **기술 이름(폴더·저장소·패키지)**: `GaindB`
- **성격**: MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구. 원본 MP3Gain 의 기능·동작·태그 포맷·출력을 Python 으로 **빠짐없이 동일하게 재현**하는 것을 목표로 한다. 단, 원본 C 코드를 옮기는 "포팅"이 아니라 공개 사양·관찰된 동작만 보고 독립 구현하는 **clean-room 재구현**이다(상세는 1.2·4 참조).
- **범위**: **MP3 단독 전용**. AAC/FLAC/Opus 등 타 포맷은 다루지 않는다(원본 mp3gain 본체도 MP3 전용이며 AAC 는 별도 빌드. 사유는 5·10 참조).
- **위치**: AVD(AV_Downloader)로 "MP3 지정" 다운로드한 음원의 음량을 고르게 맞추는 **후속 단계 도구**. 단독으로도 동작.
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\GaindB`
- **장기 비전**: GaindB(코어+CLI) 완성 후 PySide6 GUI 를 얹어 Windows·macOS 크로스플랫폼 프로그램으로 만든다(6단계). 나아가 기존 AVD 프로젝트(https://github.com/metapbl/AVD)와 병합해 다기능 유틸리티로 발전시키는 것이 큰 그림이다(병합은 6단계 이후의 비전이며, 현재 당면 목표는 GaindB 자체의 완성과 GUI MVP).
- **라이선스 방침**: 1.2·4 참조 (clean-room 우선, 개인 로컬 사용).

## 1.1. 원본 동일 재현 원칙 (최우선 원칙)

- 원본 mp3gain 의 **기능·동작·태그 포맷·출력·옵션을 빠짐없이 그대로 재현**한다. 임의로 기능을 빼거나 단순화하지 않는다.
- 불가피하게 일부를 미루거나 예외를 두어야 할 때는 **Claude 가 임의로 정하지 않는다.** 반드시 사용자와 합의하고, 그 결정을 12.1 진척 로그에 "축소가 아니라 합의된 예외 / 진행 중 미완"임이 드러나게 명시한다.
- "동일 재현"은 **결과(동작·태그 포맷·출력·수치)의 일치**를 뜻한다. 그 구현은 원본 C 코드를 옮기지 않고 공개 사양·관찰된 동작으로 독립 작성한다 — 즉 동일 재현과 clean-room(1.2·4)은 모순되지 않는다(결과는 일치, 코드는 독립).
- 아래는 사용자와 **이미 합의된 예외/우선 구현**이다. 이는 기능 축소가 아니다.
  - **디코더(항구적 예외)**: PCM 추출은 원본의 `mpglibDBL` 디코더를 포팅하지 않고 외부 도구(ffmpeg)를 호출한다. LGPL 분리·실용성 때문이며, 구현 수단만 다를 뿐 **분석 결과(라우드니스 dB)는 원본과 일치**시킨다(7 참조).
  - **샘플레이트(우선 구현·확장 대상)**: 실제 음원의 절대다수가 44.1k·48k 이므로 이 둘을 먼저 구현·검증했다. 원본은 ReplayGain 사양의 모든 샘플레이트 계수를 지원하므로, 나머지 샘플레이트도 원칙상 추가 대상이다(축소가 아니라 미완. 상세는 12.1).

## 1.2. clean-room 전면 적용 (프로젝트 전체 원칙)

이 프로젝트의 **모든 구성 요소**는 clean-room 으로 작성한다 — 지금까지의 코어(`gaindb/`)·CLI 는 물론, 앞으로 추가될 GUI(6단계)와 그 이후 어떤 확장이든 예외 없이 적용된다. 원본 MP3Gain 의 어떤 코드(C 본체든 VB GUI 든)도 직접 번역·복붙하지 않는다. 다른 언어로 옮기는 것도 2차적 저작물이므로 금지한다. 우리가 차용하는 것은 **저작권 대상이 아닌 것** — 알고리즘, 파일·태그 포맷, 비트 레이아웃, 옵션 체계, 화면 구성·동작 같은 공개 사양과 관찰된 동작뿐이다. 그 위에서 결과(동작·포맷·출력·외관)는 원본과 일치시키되 코드는 독립 작성한다. 원본 소스(C·GUI 모두)는 사양·동작 이해 목적의 참고 자료로만 로컬 보관하며 git 에서 제외한다(LGPL 분리). 이 원칙은 1.1·4·10.2 와 한 몸이며, 어떤 압축·개정에서도 약화시키지 않는다.

## 2. 프로젝트 구조

루트: `C:\Users\ggoyo_zhxlvdr\GaindB`

```
GaindB/
├─ gaindb/                 # 패키지
│  ├─ __init__.py
│  ├─ frame.py             # [1단계] 프레임 파서: _BitReader, 헤더 파싱, global_gain 읽기
│  ├─ writer.py            # [1단계] global_gain ±N 무손실 적용 + CRC 재계산
│  ├─ decode.py            # [2/3단계] ffmpeg/ffprobe 로 MP3→PCM
│  ├─ id3.py              # [5단계 ⑤] ID3v2 태그(RVA2 + TXXX) 읽기/쓰기
│  └─ analysis.py          # [2단계] ReplayGain 분석(Track/Album), dB→스텝 변환
├─ apply_gain.py           # [1·2단계] CLI: 수동/auto/album 게인 적용
├─ mp3gain_cli.py          # [5단계] 통합 CLI 진입점(원본 mp3gain 옵션 체계 재현)
├─ mp3gain/                # 원본 C·GUI 소스(LGPL, 사양 참고용). git 제외
│  ├─ LICENSE  Makefile  README.md
│  ├─ src/
│  │  ├─ mp3gain.c / .h        # [참고 완료] 프레임 파싱 + global_gain 적용 + 메인 흐름
│  │  ├─ gain_analysis.c / .h  # [참고 완료] ReplayGain 필터 계수·RMS·통계
│  │  ├─ apetag.c / .h         # [참고 완료] APEv2 태그(전 필드 + undo)
│  │  ├─ id3tag.c / .h         # [참고 완료] ID3v2 태그(RVA2 + TXXX)
│  │  ├─ rg_error.c / .h       # 오류 처리(보조)
│  │  └─ (replaygaindll.*, *.dsp/.dsw/.sln/.vcproj/.rc, resource.h, Makefile — 빌드·래퍼, 무시)
│  └─ mp3gain-win-gui-1_3_4-src/  # 원본 Windows GUI(VB) 소스. 6단계 외관·동작 참고용(clean-room, 복붙 금지)
├─ CLAUDE.md               # 이 컨텍스트 파일
├─ CopyClaudeMd.bat        # CLAUDE.md 사본 동기화 스크립트
├─ .gitignore
├─ 10cm - 사랑은 은하수 다방에서.mp3   # 테스트 음원(git 제외, 48k)
└─ Debussy - Arabesque No.1.mp3       # 테스트 음원(git 제외, 44.1k)
```

(구조가 바뀌면 이 트리와 12.1 진척 로그를 함께 갱신한다. `mp3gain/` 하위 전체는 git 제외 — 원본 C·GUI 소스 모두 LGPL 분리 대상.)

## 3. 협업 모델

- **작업 방식**: 1인 개발자 + AI 페어 프로그래밍.
- **성격**: 원본 mp3gain 의 기능을 완전히 재현하면 코어·CLI 가 완성되는 유틸리티(이후 GUI 가 6단계로 이어짐).
- **버전관리**: 로컬 Git (원격 저장소 없음 기본, 단계별 커밋으로 안전망 확보). 공개는 최후의 선택지.
- **이 파일 관리**: 컨텍스트 파일은 짧게 유지한다. 단계 완료 시 12.1 진척 로그만 갱신하고, 끝난 단계의 세부 구현 설명은 한두 줄 요약으로 압축한다. 새 항목 추가 시 기존 항목과 중복·비대화되지 않게 한다. **단, 1.1 원본 동일 재현 원칙·1.2 clean-room 전면 원칙을 약화시키는 방향으로는 압축·수정하지 않는다.** (진척 로그 압축은 D-3 와 함께 일괄 수행 예정 — 완료된 것의 how 는 압축, 합의·미완·제약의 what 은 보존.)

## 4. 라이선스 방침

- 원본 MP3Gain 은 C 로 작성된 **LGPL v2.1** 오픈소스(2009년경 개발 중단). Windows GUI(MP3GainGUI)도 LGPL.
- **clean-room 방식(1.2 전면 적용)**: 원본 C·VB 코드를 직접 번역(복붙)하지 않고, 공개된 사양(ReplayGain 알고리즘, MPEG 오디오 프레임 구조, 태그 포맷, GUI 화면 구성·동작)과 관찰된 동작만 보고 독립 구현한다. 알고리즘·파일 포맷·태그 포맷·UI 동작은 저작권 대상이 아니므로 LGPL 구속을 피할 수 있음.
- 원본 코드를 그대로 번역하면 결과물에 LGPL 이 따라옴. 다른 언어로 옮겨도 2차적 저작물로 간주됨. 그러므로 **결과(동작·포맷·출력·외관)는 원본과 일치시키되, 코드는 독립 작성**한다(1.1·1.2 참조).
- 개인 로컬 사용 중에는 "배포"가 없으므로 LGPL 의무는 사실상 발생하지 않음. 원본 소스(`mp3gain/`)를 git 에서 제외하는 것도 이 분리를 위함. 배포 계획이 생기면 그때 변호사 검토 필요 (PySide6 자체도 LGPL, ffmpeg 동봉 여부 등 포함. Claude 는 변호사가 아님).

## 5. 핵심 기술 원리

- **무손실 음량 조정**: MP3 각 프레임의 사이드 정보 안 `global_gain`(8bit) 필드를 직접 ±N 하여 음량 조절. 디코더는 `2^(gain/4)` 로 샘플을 곱하므로 1스텝 ≈ 1.5dB. 재인코딩 없음 → 무손실. **MP3 고유 구조라 타 포맷에 적용 불가**(범위를 MP3 전용으로 못박는 근거).
- **음량 분석**: PCM 으로 디코딩 후 David Robinson 의 ReplayGain 알고리즘(equal-loudness 필터 + RMS + 통계, 95퍼센타일 부근)으로 인지 음량 계산. 목표값(기본 89dB)에 맞추는 데 필요한 게인 스텝 수를 산출.
- **Track gain / Album gain** 두 모드. Album 은 곡별 히스토그램을 누적해 단일 dB 산출 후 전 곡에 동일 스텝 적용.
- **태그(원본 전 기능 재현 대상)**: 원본은 APEv2(기본) 또는 ID3v2(`-s i`) 태그에 다음을 기록·읽기·갱신·제거한다 — ReplayGain 표준 필드(`REPLAYGAIN_TRACK_GAIN`/`_PEAK`, `REPLAYGAIN_ALBUM_GAIN`/`_PEAK`, ID3 는 추가로 RVA2 프레임·`replaygain_reference_loudness`), mp3gain 고유 필드(`MP3GAIN_MINMAX`, `MP3GAIN_ALBUM_MINMAX`, `MP3GAIN_UNDO`). 게인 적용 시 이 값들을 일관되게 갱신한다(undo 누적, gain 에서 dB 차감, peak 에 2^(N/4) 곱, minmax 에 N 가감 — 원본 `changeGainAndTag` 동작). undo 는 이 누적된 역방향 값으로 원복한다.

## 6. 원본 참고 자료

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `mp3gain/src/` 에 보관**(master.zip 압축 해제본, 2 트리 참조). LGPL 분리를 위해 git 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- **원본 Windows GUI(MP3GainGUI)는 VB 로 작성된, CLI `mp3gain.exe` 를 호출하는 프런트엔드**다. 소스를 로컬 `mp3gain/mp3gain-win-gui-1_3_4-src/` 에 보관(LGPL 분리 위해 git 제외). 6단계에서 화면 구성·동작을 관찰·참고하되 코드는 옮기지 않는다(1.2 clean-room). 공식 출처: SourceForge mp3gain 의 `mp3gain-win-gui-1_3_4-src.zip`.
- 단계별 대상 파일은 2 트리의 `[N단계]` 표시 참조.

## 7. 기술 스택

- **언어**: Python 3 (3.13/3.14 등). 1단계는 순수 표준 라이브러리(외부 의존성 없음).
- **신호처리**: numpy + scipy (2단계 필터·RMS·통계).
- **MP3 디코딩(PCM 추출)**: 외부 도구(ffmpeg 직접 호출) 사용 — 원본의 `mpglibDBL` 디코더는 옮기지 않는다. 이는 사용자와 합의된 항구적 예외이며(1.1 참조), 구현 수단만 다를 뿐 분석 결과 dB 는 원본과 일치시킨다. ffmpeg 는 PATH 호출(GPL 동봉 안 함, 개인 로컬).
- **GUI(6단계 예정)**: PySide6 (Qt for Python, LGPL). Windows·macOS 크로스플랫폼. AVD 프로젝트와 스택 일치(향후 병합 대비). 기존 `gaindb/` 코어 + CLI 위에 얹는 새 프런트엔드(코어 재작성 없음).
- **가상환경**: venv (`.venv`).

## 8. 구현 단계

> 아래 단계는 작업을 나누기 위한 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다**(1.1). 분량 추정은 참고용이다.

1. **[완료] MP3 프레임 파서 + `global_gain` 읽기/쓰기** — 순수 Python. 읽기·쓰기·무손실 round-trip 검증 끝(상세는 12.1).
2. **[완료] ReplayGain 분석기** (numpy/scipy) — equal-loudness 필터 + RMS + 통계, Track/Album gain, dB→스텝 변환. 44.1k·48k 검증 완료(나머지 샘플레이트는 확장 대상, 1.1·12.1).
3. **[완료] MP3 디코딩(PCM 추출)**: ffmpeg/ffprobe subprocess. 2단계 입력 공급(`gaindb/decode.py`).
4. **[완료] 태그 처리** — APEv2 읽기·쓰기·갱신·제거, scanFrameGain(min/max), changeGainAndTag 동등, undo, auto/album 태그 연결까지 완료. otherFields·Lyrics3/ID3v1 꼬리 보존. ID3v2(RVA2/TXXX)는 ⑤로 분리(아래 12.1). 검증 완료.
5. **[진행 중] CLI / 옵션 / 일괄 처리** — 원본 옵션을 빠짐없이 재현(`-r`/`-a`/`-e`/`-g`/`-l`/`-d`/`-m`/`-k`/`-c`/`-w`/`-s c|d|s|r|u|i|a`/`-u`/`-o`/`-q`/`-p`/`-x`/`-f`/`-t`/`-T` 등), 클리핑 경고·자동 클립(`-k`), database 출력(`-o`) 포함. A~D-2 완료, D-3 첫 갈래(개발용 CLI 흡수·전면 영문화) 수동 검증 완료·자동 회귀 미확인, D-3 둘째·셋째 갈래(통합 테스트 등록·로그 압축) 미착수(12.1).
6. **[착수 전 · 5단계 완료 후] GUI (PySide6, clean-room 재현)** — 원본 MP3GainGUI 의 외관·기능·동작을 PySide6 로 동일 재현하되, VB 코드를 옮기지 않고 공개 동작만 보고 독립 구현한다(1.2·4·1.1 과 동일 원칙). 기존 `gaindb/` 코어 + CLI 위에 얹는 새 프런트엔드(코어 재작성 없음). Windows·macOS 크로스플랫폼. **세부 MVP 설계(어떤 화면·버튼·옵션을 어느 순서로 넣을지)는 5단계 완료 후 사용자와 합의해 정한다**(1.1 — Claude 가 임의로 정하지 않음). 배포 시 PySide6 LGPL·ffmpeg 검토 필요(4). 원본 GUI 소스는 **VB6** (`mp3gain/mp3gain-win-gui-1_3_4-src/`, `.vbp`/`.frm`/`.frx`/`.bas`/`.cls`). 구성(관찰): 메인 창(`frmMain`)·옵션(`frmOptions`)·게인 입력(`frmGetGain`)·로그(`frmLogs`)·시스템 트레이(`frmSysTray`)·정보/기부/면책 다이얼로그, 경고 모달들(`frmStereoWarning`=단일채널 거부, `frmLayerCheckWarning`=Layer 오인, `frmSkipTagsWarn`/`frmReadOnly`/`frmResetWarn` 등); 모듈 `basLocalizer`(다국어)·`basSaveAnalysis`·`basListViewSort`·`Mp3Info.cls` 등. 다수 경고 폼은 CLI 가 이미 동작으로 재현한 상황의 GUI 대응 — 6단계에서 이 매핑을 PySide6 다이얼로그로 재현한다(화면·동작 관찰만, VB 코드 복붙 금지 — 1.2). **다국어(한국어·영어)는 GUI 계층의 책임이다(합의됨, D-3): CLI(코어+진입점)는 영문만 출력하고, 화면 표기의 다국어화는 PySide6 의 tr()/번역 파일로 GUI 에서 처리한다.** (원본 GUI 의 basLocalizer 대응.)

## 9. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만. (GUI 6단계는 macOS 동작도 목표 — 크로스플랫폼.)
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits (`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: 셸은 PowerShell 7.6.3. `>` 리다이렉션은 UTF-16 LE BOM 으로 씀. 파일 쓰기는 `... | Out-File -Encoding utf8NoBOM <파일>` 로 BOM 없는 UTF-8 을 명시한다(7.x 는 `utf8` 도 기본 BOM 없음이지만 `utf8NoBOM` 으로 통일).

## 10. Claude 응답 규칙

### 10.1. 범위 고수 (포맷)

MP3 전용이다. 타 포맷 지원 제안은 하지 않는다. 무손실 게인 조정은 MP3 `global_gain` 필드 기법이라 타 포맷에 원리적으로 적용 불가. (이는 포맷 범위 규정일 뿐, 원본 기능 축소가 아니다 — 원본 mp3gain 본체도 MP3 전용.)

### 10.2. 원본 동일 재현 + clean-room 준수

- 원본 기능을 **임의로 빼거나 단순화하지 않는다**(1.1). 무언가를 미루거나 예외로 두려면 먼저 사용자와 합의하고 12.1 에 명시한다.
- 사용자가 제공한 원본 C·VB 소스는 **사양·동작 이해 목적으로만** 읽고, 코드를 그대로 옮기지 않는다(1.2 전면 적용). 알고리즘·비트 레이아웃·필터 계수·태그 포맷·UI 동작 같은 공개 사양만 차용해 독립 재작성한다.

### 10.3. 코드 제시 단위

- 변경이 **함수 2개 이하**에서만 일어나고 모듈 최상위를 안 건드리면 → 변경된 함수를 **개별 코드 블록으로 함수 단위 발췌**.
- 그 외(함수 3개 이상·최상위 변경·새 함수·시그니처 변경) → **파일 전체**.
- 어느 경우든 코드 블록 바깥에 변경 지점을 한 문장으로 명시.

### 10.4. 코드 제시 전 확인

코드 블록을 보내기 전 "코드를 보내드릴까요?" 라고 한 박자 묻고, 동의 후 다음 응답에서 제시한다. 설계·진단·합의가 코드보다 앞에 온다.

### 10.5. 터미널 명령 동봉

파일을 수정·추가·삭제하는 코드를 제시할 때는 디스크 반영·커밋 명령을 같은 응답에 함께 제시. 기본 흐름 ① `git add <파일>` ② `git status` ③ `git commit -m "..."`. (원격 저장소 없으므로 `git push` 생략.) 환경은 PowerShell, cwd=루트. 신규 파일·디렉터리는 `New-Item -ItemType {Directory|File} -Force` 로 만든 뒤 본문은 VS Code 에 붙여 넣음 — `-Force` 는 기존 파일을 빈 파일로 덮으므로 한 줄 경고.
- **파일 전체 제시 시 터미널 붙여넣기 방식(합의됨)**: `.py` 등 파일 **전체를 새로 쓰거나 통째로 교체**할 때는, 사용자가 파일을 직접 열지 않고 VS Code 통합 터미널에 명령 한 덩어리를 붙여넣어 엔터만 치면 저장되도록 제시한다. 형식: 코드 전체를 `@'` … `'@` 리터럴 here-string 으로 감싸 `| Out-File -FilePath <경로> -Encoding utf8NoBOM` 로 파이프. (리터럴 here-string 이라 백틱·`$`·따옴표가 안전. 단, 코드에 줄 맨 앞이 `'@` 인 줄이 없어야 함 — 제시 전 확인.) 이 편의를 위해 코드는 **가급적 파일 전체 단위로 제시**한다(10.3 의 함수 발췌보다 전체 파일을 우선). 부분 발췌가 꼭 필요한 극소수 경우만 VS Code 직접 편집.


### 10.6. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 있으면 바깥 펜스는 안쪽보다 백틱을 하나 더 쓴다(안쪽 3개 → 바깥 4개).

### 10.7. 서식

- 불릿은 `-` + 공백 1칸, 하위 불릿은 부모 기준 2칸 들여쓰기.
- `##`/`###` 헤더에 1, 1.1 형식 번호(깊이 2까지).
- 과한 볼드·리스트 남용 지양, 산문 우선.

## 11. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 1단계의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함. (1단계에서 해결·검증 완료.)
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain·255-gain 프레임은 클램프로 비가역**: `gain==0` 이면 ±N 으로 안 바뀌고(하한 유지), `gain==255` 인 프레임에 +N 하면 255 로 클램프되어 초과분이 소실된다(상한). 따라서 round-trip 완전복원은 이 경계 프레임이 없거나, 경계를 벗어나지 않는 방향으로 적용할 때만 보장된다(원본 `_apply_one` 동작 동일). 통합 테스트의 round-trip 은 상한 255 회피를 위해 음수 스텝 먼저(-3) 후 복원(+3 또는 undo)으로 한다 — ffmpeg 변형 fixture(test_mono_44k / test_stereo_44k)의 max global_gain 이 255(오른쪽 채널)라 이 방향이 필수임이 D-3 통합 테스트에서 실증됨. (적용된 파일을 재계산하면 적용분이 반영된 "현재 상태"의 min/max·dB 가 나오는 것이 정상 — D-2 검증 관찰.)
- **타 포맷 적용 불가**(10.1) / **원본 코드 직접 번역 금지**(1.2·4·10.2) / **원본 기능 임의 축소 금지**(1.1·10.2).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 그래서 C·VB 소스는 로컬 보관 + 사용자가 붙여넣어 제공(6 참조). Claude 가 크롤로 가져오려 시도하지 말 것.
- **테스트는 원본 음원을 절대 건드리지 않는다(영구 제약, D-3 오염 사고 교훈)**: 모든 검증·테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다. 각 테스트는 깨끗한 fixture(또는 `-s d` 로 태그 제거한 상태)에서 시작한다. 이번 세션에서 옛 verify_*.py 가 원본 두 음원에 mp3gain 태그를 남겨, round-trip 해시가 어긋나 보이는 사고가 있었다(코드 결함 아님, 원본 오염 탓). 두 음원은 세션 끝에 순수 상태로 복구함.
- **undo 0 태그는 남는다(원본 동일 동작)**: 깨끗한 파일에 `-g N` 적용 후 `-u` 하면 오디오 본문은 비트 동일로 복원되지만 `MP3GAIN_UNDO 0,0` APE 태그가 남아 파일 전체 해시는 달라진다(원본 changeGainAndTag 의 "don't remove it" 동작). 무손실 검증은 전체 해시가 아니라 tag_offset 까지의 오디오 본문 해시로 판정한다.

## 12. 새 세션 시작 방법

새 세션 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다. (`CopyClaudeMd.bat` 실행 → 채팅 입력창에 Ctrl+V 로 파일 첨부.) 이어 그 세션 단계에 필요한 C 소스(.c/.h) 또는 GUI 소스를 붙여넣어 제공한다. 검색 도구는 최신 정보 확인용으로만 쓰고, 원본 소스 입수에는 쓰지 않는다.

### 12.1. 진척 로그 / 다음 세션 시작점

**1~4단계 완료·검증 완료.** 1) 프레임 파서 + `global_gain` 읽기/쓰기(`gaindb/frame.py`·`writer.py`, round-trip 바이트 동일). 2) ReplayGain 분석기(`gaindb/analysis.py` — equal-loudness 필터+RMS+히스토그램+95퍼센타일−PINK_REF, `db_to_steps`; Track은 ffmpeg replaygain과 0.02dB 이내, Album은 44.1k+48k 혼합 검증). 3) MP3 디코딩(`gaindb/decode.py` — ffmpeg/ffprobe subprocess, ±32768 스케일). 4) 태그(`gaindb/tag.py` APE·`gaindb/id3.py` ID3v2 — read/write/remove/round-trip, scan_gain, change_gain_and_tag[undo 누적·gain 차감·peak ×2^(N/4)·minmax], auto/album 연결, otherFields·Lyrics3/ID3v1 꼬리 보존, useId3 분기).

- **샘플레이트(합의된 미완, 1.1)**: 44.1k·48k 우선 구현·검증. 나머지 ReplayGain 계수는 확장 대상(축소 아님).
- **48k 관찰**: 한 테스트 곡 `track_peak>1.0`(1.033) — 클립 방지(-k)에서 의미, 게인 산출엔 무영향.

**5단계 완료·검증 완료** (CLI / 옵션 / 일괄 처리). `mp3gain_cli.py` — 원본 옵션을 빠짐없이 재현(직접 게인 `-g`/`-l`/`-u`, 분석·적용 `-r`/`-a`/`-e`/`-x`/`-m`/`-d`, 클립 `-k`/`-c`, database `-o`, 태그 `-s c|d|s|r|u|i|a`, 출력·동작 `-t`/`-T`/`-q`/`-p`/`-f`/`-w`/`-v`/`-h`/`-?`). recalc 비트마스크(FULL/AMP/MIN_MAX)로 디코딩 스킵(ffmpeg 디코더 예외 1.1의 귀결) — 결과 수치는 원본 동일, 디코딩 횟수만 다름. curAlbum 비교는 원본대로 부동소수 정확 일치(epsilon 미도입, 합의됨). 개발용 CLI는 `--debug-scan`/`--debug-tag`로 흡수. CLI I/O는 영문만 출력(다국어는 6단계 GUI tr() 책임 — 합의됨); docstring·주석만 한국어.

**통합 테스트 스위트 완성 (tests/, unittest, 외부 의존 없음).** `python -m unittest discover -s tests` 로 60건 실행·전부 PASS. 옛 verify_*.py 8개를 대체·흡수하고 삭제(아래 매핑). 모든 테스트는 원본 음원 불간섭 — tempfile 사본에서만 동작, `FixtureGuard`가 원본 해시로 오염 감시, 무결성 판정은 `audio_body_sha256`(프레임 구간; 태그 생성·undo 0 잔존과 무관). 구성:

- `_support.py` — REPO_ROOT/MP3_DIR(환경변수 `GAINDB_TEST_MP3_DIR` 우선), `KNOWN_FIXTURES`, `BaseGainTest`(사본·가드·`run_cli`[subprocess, UTF-8 강제 — 비-ASCII 파일명 대응]·`audio_body_sha256`).
- `test_support_smoke`(3) / `test_roundtrip_options`(9: round-trip·`-l` 채널모드·`-v`/`-h`) / `test_analysis_integration`(6: 제안·`-o`·Album·`-r`/`-a`·CLI dB↔코어 대조) / `test_tag_integration`(7: APE·ID3 write/read/remove/round-trip) / `test_options_parsing`(9: parse_args 단위) / `test_recalc_decode_skip`(5: in-process·decode_pcm 카운트·`-s u`/`-s r`·update tags) / `test_cli_misc`(11: `-x`·`-d`/`-m` 순서·No changes·`-s s`·클립 공식·`-c`·`-s c` 수치/비파괴/11칸) / `test_useid3_migration`(4: stale APE 제거·read 순서·dirty 업그레이드·음수 반환).
- **verify_* → 통합 스위트 매핑**: cli_ab→options_parsing+roundtrip/tag, c1→analysis+cli_misc, c2→analysis/tag+cli_misc, c3→clip+cli_misc, d1→tag+cli_misc, d2→recalc_decode_skip, 5c→useid3_migration.
- **mutagen 상호운용은 통합 스위트 밖(합의됨)**: `verify_id3_read.py`·`verify_id3_write.py`는 원본 mp3gain 동작이 아니라 외부 도구(mutagen) 상호운용 검증이라, mutagen 부재 환경 skip 오염을 피해 `manual_checks/`(git 제외, `.gitignore` 등록)에 로컬 보존·수동 실행.

**테스트 fixture(ffmpeg 변형, git 제외·합의됨 1.1)**: Debussy(44.1k)에서 채널 모드 커버리지용 생성 — mono(mode 3) `ffmpeg -i "Debussy - Arabesque No.1.mp3" -ac 1 -c:a libmp3lame -q:a 4 test_mono_44k.mp3`, stereo(mode 0) `... -ac 2 -joint_stereo 0 ... test_stereo_44k.mp3`. 둘 다 MPEG1·44100·CRC=no, max global_gain=255 포함(R 채널). MPEG2/2.5 변형은 샘플레이트 확장(1.1 미완) 때 함께 추가 예정.

**테스트 음원 상태**: Debussy(44.1k)·10cm(48k) 원본은 mp3gain 태그 없는 순수 상태(128바이트 ID3v1 꼬리만). 변형 fixture(test_mono_44k·test_stereo_44k)는 git 제외 생성물. 통합 테스트는 전부 tempfile 사본에서 시작.

**다음 = 6단계 GUI (PySide6, clean-room 재현).** 5단계 완료. 세부 MVP 설계(화면·버튼·옵션 순서, 다국어 tr())는 착수 전 사용자와 합의(8항목 6단계). 코어 재작성 없이 `gaindb/`+CLI 위에 얹는 프런트엔드.
