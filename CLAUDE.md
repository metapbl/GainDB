# Gain dB — Claude 컨텍스트 파일

> 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하는 컨텍스트 파일.
> 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고, 그 세션 단계에 필요한 원본 소스를 함께 붙여넣는다(자세한 방법은 "5. 원본 참고 자료 · 새 세션 시작법" 참조).

---

## 1. 프로젝트 정체성

- **표시 이름**: Gain dB / **기술 이름(폴더·저장소·패키지)**: `GaindB`
- **성격**: MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구. 원본 MP3Gain 의 기능·동작·태그 포맷·출력을 Python 으로 **빠짐없이 동일하게 재현**하는 것을 목표로 하되, 원본 C 코드를 옮기는 "포팅"이 아니라 공개 사양·관찰된 동작만 보고 독립 구현하는 **clean-room 재구현**이다(원칙 상세는 2 참조).
- **범위**: **MP3 단독 전용**. AAC/FLAC/Opus 등 타 포맷은 다루지 않는다(원본 mp3gain 본체도 MP3 전용, 무손실 게인 기법이 MP3 고유 구조라 타 포맷에 원리적으로 적용 불가 — 3 참조).
- **위치**: AVD(AV_Downloader)로 "MP3 지정" 다운로드한 음원의 음량을 고르게 맞추는 **후속 단계 도구**. 단독으로도 동작.
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\GaindB`
- **협업 모델**: 1인 개발자 + AI 페어 프로그래밍. 버전관리는 로컬 Git(원격 없음 기본, 단계별 커밋으로 안전망 확보, 공개는 최후의 선택지).
- **장기 비전**: GaindB(코어+CLI) 완성 후 PySide6 GUI 를 얹어 Windows·macOS 크로스플랫폼 프로그램으로 만든다(8단계). 나아가 기존 AVD 프로젝트(https://github.com/metapbl/AVD)와 병합해 다기능 유틸리티로 발전시키는 것이 큰 그림이다(병합은 그 이후의 비전이며, 당면 목표는 GaindB 자체의 완성과 GUI MVP).

## 2. 핵심 원칙 (최우선 · 어떤 압축·개정에서도 약화 금지)

프로젝트 전체를 관통하는 세 원칙이며 서로 한 몸이다: 원본 동일 재현, clean-room 전면 적용, 그 위의 라이선스 방침. 완료분의 how 는 압축해도, 이 원칙과 합의·미완·제약의 what 은 보존한다.

### 2.1. 원본 동일 재현

- 원본 mp3gain 의 **기능·동작·태그 포맷·출력·옵션을 빠짐없이 그대로 재현**한다. 임의로 기능을 빼거나 단순화하지 않는다.
- "동일 재현"은 **결과(동작·태그 포맷·출력·수치)의 일치**를 뜻한다. 구현은 원본 C 코드를 옮기지 않고 공개 사양·관찰된 동작으로 독립 작성한다 — 즉 동일 재현과 clean-room 은 모순되지 않는다(결과는 일치, 코드는 독립).
- 불가피하게 일부를 미루거나 예외를 두어야 할 때 **Claude 가 임의로 정하지 않는다.** 반드시 사용자와 합의하고, 그 결정을 10 진척 로그에 "축소가 아니라 합의된 예외 / 진행 중 미완"임이 드러나게 명시한다.
- 이미 합의된 예외/우선 구현(기능 축소가 아님):
  - **디코더(항구적 예외)**: PCM 추출은 원본의 `mpglibDBL` 디코더를 포팅하지 않고 외부 도구(ffmpeg)를 호출한다. LGPL 분리·실용성 때문이며, 구현 수단만 다를 뿐 분석 결과(라우드니스 dB)는 원본과 일치시킨다(2.3 참조).
  - **샘플레이트(확장 완료)**: 실제 음원 다수인 44.1k·48k 를 먼저 구현·검증한 뒤, ReplayGain 사양의 나머지 샘플레이트(32k 및 MPEG2/2.5 계열)까지 확장·검증 완료. 계수는 공개 표준값 전사(재설계 불가 사유·clean-room 판단은 10.2).

### 2.2. clean-room 전면 적용

이 프로젝트의 **모든 구성 요소**는 clean-room 으로 작성한다 — 코어(`gaindb/`)·CLI 는 물론, GUI(8단계)와 그 이후 어떤 확장이든 예외 없이 적용된다. 원본 MP3Gain 의 어떤 코드(C 본체든 VB GUI 든)도 직접 번역·복붙하지 않는다. 다른 언어로 옮기는 것도 2차적 저작물이므로 금지한다. 우리가 차용하는 것은 **저작권 대상이 아닌 것** — 알고리즘, 파일·태그 포맷, 비트 레이아웃, 필터 계수 수치, 옵션 체계, 화면 구성·동작 같은 공개 사양과 관찰된 동작뿐이다. 그 위에서 결과(동작·포맷·출력·외관)는 원본과 일치시키되 코드는 독립 작성한다. 원본 소스(C·GUI 모두)는 사양·동작 이해 목적의 참고 자료로만 로컬 보관하며 git 에서 제외한다(LGPL 분리).

### 2.3. 라이선스 방침

- 원본 MP3Gain 은 C 로 작성된 **LGPL v2.1** 오픈소스(2009년경 개발 중단). Windows GUI(MP3GainGUI)도 LGPL.
- 원본 코드를 그대로 번역하면 결과물에 LGPL 이 따라오고, 다른 언어로 옮겨도 2차적 저작물로 간주된다. 그래서 clean-room(2.2)으로 결과만 일치시키고 코드는 독립 작성한다. 알고리즘·파일 포맷·태그 포맷·UI 동작은 저작권 대상이 아니므로 LGPL 구속을 피할 수 있다.
- 개인 로컬 사용 중에는 "배포"가 없으므로 LGPL 의무는 사실상 발생하지 않는다. 원본 소스(`mp3gain/`)를 git 에서 제외하는 것도 이 분리를 위함.
- 배포 계획이 생기면 GPT·Claude 최신 모델 교차검증으로 1차 법적 검토(쟁점·조항·리스크 정리)를 하되, 실제 공개 배포 직전의 최종 확인은 자격 있는 전문가(변호사) 검토를 남겨둔다(PySide6 자체도 LGPL, ffmpeg 동봉 여부 등 포함). **AI 는 성능·교차 여부와 무관하게 법적 책임·자격을 대체하지 못한다.**

## 3. 핵심 기술 원리

- **무손실 음량 조정**: MP3 각 프레임의 사이드 정보 안 `global_gain`(8bit) 필드를 직접 ±N 하여 음량 조절. 디코더는 `2^(gain/4)` 로 샘플을 곱하므로 1스텝 ≈ 1.5dB. 재인코딩 없음 → 무손실. **MP3 고유 구조라 타 포맷에 적용 불가**(범위를 MP3 전용으로 못박는 근거).
- **음량 분석**: PCM 으로 디코딩 후 David Robinson 의 ReplayGain 알고리즘(equal-loudness 필터 + RMS + 통계, 95퍼센타일 부근)으로 인지 음량 계산. 목표값(기본 89dB)에 맞추는 데 필요한 게인 스텝 수를 산출.
- **Track gain / Album gain** 두 모드. Album 은 곡별 히스토그램을 누적해 단일 dB 산출 후 전 곡에 동일 스텝 적용.
- **태그(원본 전 기능 재현 대상)**: 원본은 APEv2(기본) 또는 ID3v2(`-s i`) 태그에 다음을 기록·읽기·갱신·제거한다 — ReplayGain 표준 필드(`REPLAYGAIN_TRACK_GAIN`/`_PEAK`, `REPLAYGAIN_ALBUM_GAIN`/`_PEAK`, ID3 는 추가로 RVA2 프레임·`replaygain_reference_loudness`), mp3gain 고유 필드(`MP3GAIN_MINMAX`, `MP3GAIN_ALBUM_MINMAX`, `MP3GAIN_UNDO`). 게인 적용 시 이 값들을 일관되게 갱신한다(undo 누적, gain 에서 dB 차감, peak 에 2^(N/4) 곱, minmax 에 N 가감 — 원본 `changeGainAndTag` 동작). undo 는 이 누적된 역방향 값으로 원복한다.

## 4. 기술 스택 · 저장소 구조

- **언어**: Python 3 (3.13/3.14 등). 프레임 파서·writer 는 순수 표준 라이브러리(외부 의존성 없음).
- **신호처리**: numpy + scipy (필터·RMS·통계).
- **MP3 디코딩(PCM 추출)**: 외부 도구(ffmpeg 직접 호출) — 원본 `mpglibDBL` 디코더는 옮기지 않는다(2.1 합의된 항구적 예외). ffmpeg 는 PATH 호출(GPL 동봉 안 함, 개인 로컬).
- **GUI**: PySide6 (Qt for Python, LGPL). Windows·macOS 크로스플랫폼. AVD 프로젝트와 스택 일치(향후 병합 대비). 기존 `gaindb/` 코어 + CLI 위에 얹는 프런트엔드(코어 재작성 없음).
- **가상환경**: venv (`.venv`).

루트: `C:\Users\ggoyo_zhxlvdr\GaindB` (구조가 바뀌면 이 트리와 10 진척 로그를 함께 갱신한다.)

GaindB/
├─ gaindb/                 # 패키지
│  ├─ __init__.py
│  ├─ frame.py             # 프레임 파서: _BitReader, 헤더 파싱, global_gain 읽기
│  ├─ writer.py            # global_gain ±N 무손실 적용 + CRC 재계산
│  ├─ decode.py            # ffmpeg/ffprobe 로 MP3→PCM
│  ├─ id3.py               # ID3v2 태그(RVA2 + TXXX) 읽기/쓰기
│  ├─ tag.py               # APEv2 태그(전 필드 + undo)
│  └─ analysis.py          # ReplayGain 분석(Track/Album), dB→스텝 변환
├─ apply_gain.py           # CLI: 수동/auto/album 게인 적용
├─ mp3gain_cli.py          # 통합 CLI 진입점(원본 mp3gain 옵션 체계 재현)
├─ tests/                  # 통합 테스트 스위트(unittest, 외부 의존 없음)
├─ manual_checks/          # 통합 스위트 밖 로컬 수동 검증(git 제외, mutagen/exe 상호운용·대조)
│  ├─ compare_exe_lowrate.py   # 6단계 저샘플레이트 dB를 원본 exe와 -o -s s 대조(사본·scan only)
│  ├─ verify_id3_read.py       # 4단계 ID3v2 읽기 경로 검증(mutagen으로 작성→우리 read)
│  └─ verify_id3_write.py      # 4단계 ID3v2 쓰기 경로 검증(우리 write→mutagen read, round-trip)
├─ mp3gain/                # 원본 C·GUI 소스(LGPL, 사양 참고용). git 제외
│  ├─ LICENSE  Makefile  README.md
│  ├─ src/
│  │  ├─ mp3gain.c / .h        # [참고 완료] 프레임 파싱 + global_gain 적용 + 메인 흐름
│  │  ├─ gain_analysis.c / .h  # [참고 완료] ReplayGain 필터 계수·RMS·통계
│  │  ├─ apetag.c / .h         # [참고 완료] APEv2 태그(전 필드 + undo)
│  │  ├─ id3tag.c / .h         # [참고 완료] ID3v2 태그(RVA2 + TXXX)
│  │  ├─ rg_error.c / .h       # 오류 처리(보조)
│  │  ├─ mp3gain.exe           # [검증 기준] MSYS2+MinGW 로 빌드한 원본 1.6.2 CLI. git 제외
│  │  └─ (replaygaindll.*, *.dsp/.dsw/.sln/.vcproj/.rc, resource.h, Makefile — 빌드·래퍼, 무시)
│  └─ mp3gain-win-gui-1_3_4-src/  # 원본 Windows GUI(VB6) 소스. 8단계 참고용(clean-room, 복붙 금지)
│     ├─ frmMain.frm / Mp3Info.cls    # [참고 완료] 메인 창·DispJunk 표시 로직 / 스텝 산출(RadioMp3Gain 등)
│     ├─ frmOptions.frm  frmGetGain.frm   # 옵션·게인입력 창(8단계 참고 예정)
│     ├─ 경고 폼: frmStereoWarning/frmLayerCheckWarning/frmSkipTagsWarn/frmReadOnly/frmResetWarn (CLI 동작의 GUI 대응)
│     ├─ 모듈: basLocalizer(다국어)·basListViewSort·basSaveAnalysis
│     ├─ frmMaximizing.frm  # Max No-clip(MVP 제외)
│     └─ (frmAbout/Disclaimer/Donate/Logs/SysTray, basCommandOutput[subprocess 파싱—미재현] 등 나머지 .frm/.bas/.frx/.vbp/.res)
├─ docs/
│  └─ LICENSE_REVIEW.md    # 7단계 배포 라이선스 1차 점검 기록
├─ CLAUDE.md               # 이 컨텍스트 파일
├─ CopyClaudeMd.bat        # CLAUDE.md 사본 동기화 스크립트
├─ .gitignore
├─ 10cm - 사랑은 은하수 다방에서.mp3   # 원본 테스트 음원(git 제외, 48k, 순수 상태)
├─ Debussy - Arabesque No.1.mp3       # 원본 테스트 음원(git 제외, 44.1k, 순수 상태)
└─ test_*.mp3                          # ffmpeg 변형 fixture 11개(git 제외): test_{8k,11k,12k,16k,22k,24k,32k}, test_stereo_44k, test_mono_{12k,24k,44k}. 상세는 10 로그(4·6단계)


`mp3gain/` 하위 전체는 git 제외 — 원본 C·GUI 소스, 빌드 산출물 `mp3gain.exe` 모두 LGPL 분리 대상. exe 는 코드가 아니라 실행 결과만 검증 기준으로 쓰므로 clean-room 위반이 아니다(2.2 의 "관찰된 동작 차용").

## 5. 원본 참고 자료 · 새 세션 시작법

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `mp3gain/src/` 에 보관**(master.zip 압축 해제본). LGPL 분리를 위해 git 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- **원본 Windows GUI(MP3GainGUI)는 VB 로 작성된, CLI `mp3gain.exe` 를 호출하는 프런트엔드**다. 소스를 로컬 `mp3gain/mp3gain-win-gui-1_3_4-src/` 에 보관(git 제외). 8단계에서 화면 구성·동작을 관찰·참고하되 코드는 옮기지 않는다(2.2). 공식 출처: SourceForge mp3gain 의 `mp3gain-win-gui-1_3_4-src.zip`.
- **이 미러의 `.c` 는 크롤 불가**(`application/octet-stream` MIME). 그래서 C·VB 소스는 로컬 보관 + 사용자가 붙여넣어 제공. Claude 가 크롤로 가져오려 시도하지 말 것.
- **새 세션 시작**: 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다(`CopyClaudeMd.bat` 실행 → 채팅 입력창에 Ctrl+V). 이어 그 세션 단계에 필요한 소스(.c/.h 또는 GUI)를 붙여넣어 제공한다. 검색 도구는 최신 정보 확인용으로만 쓰고, 원본 소스 입수에는 쓰지 않는다.

## 6. 구현 단계 로드맵

> 작업을 나누기 위한 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다**(2.1). 각 단계의 완료 세부·확정된 결정은 10 참조.

1. **[완료] MP3 프레임 파서 + `global_gain` 읽기/쓰기** — 순수 Python. 읽기·쓰기·무손실 round-trip 검증.
2. **[완료] ReplayGain 분석기** (numpy/scipy) — equal-loudness 필터 + RMS + 통계, Track/Album gain, dB→스텝 변환.
3. **[완료] MP3 디코딩(PCM 추출)** — ffmpeg/ffprobe subprocess.
4. **[완료] 태그 처리** — APEv2·ID3v2 읽기·쓰기·갱신·제거, scanFrameGain, changeGainAndTag 동등, undo, auto/album 연결.
5. **[완료] CLI / 옵션 / 일괄 처리** — 원본 옵션 전부 재현, 클리핑 경고·자동 클립(`-k`), database 출력(`-o`) 포함. 통합 테스트 스위트로 검증.
6. **[완료] 샘플레이트 확장(원본 동일 재현 완결)** — ReplayGain 사양 전 샘플레이트를 코어에 추가·검증.
7. **[완료] 배포 라이선스 정합성 준비·검토** — clean-room 자체 점검 + LGPL 구속 회피 근거 정리. AI 교차검증 1차 수행. **실제 공개 배포 직전의 최종 확인은 자격 있는 전문가(변호사) 검토를 남겨둔다(2.3). 로컬 개인 사용 단계에선 불필요.**
8. **[MVP 완료·잔여 점검 중] GUI (PySide6, clean-room 재현)** — 원본 MP3GainGUI 의 외관·기능·동작을 PySide6 로 동일 재현하되 VB 코드를 옮기지 않고 공개 동작만 보고 독립 구현(2). 기존 코어 + CLI 위에 얹는 프런트엔드. Windows·macOS 크로스플랫폼. 확정된 아키텍처·MVP 범위·표시 정책·AVD 연결·잔여 항목은 **10.2·10.3 참조**.

## 7. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell 7.6.3). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만. (GUI 는 macOS 동작도 목표.)
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits(`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: `>` 리다이렉션은 UTF-16 LE BOM 으로 쓴다. 파일 쓰기는 `... | Out-File -Encoding utf8NoBOM <파일>` 로 BOM 없는 UTF-8 을 명시한다.
- **이 파일 관리**: 컨텍스트 파일은 짧게 유지한다. 단계 완료 시 10 진척 로그만 갱신하고, 끝난 단계의 세부 구현 설명은 한두 줄로 압축한다. **단, 2 핵심 원칙을 약화시키는 방향으로는 압축·수정하지 않는다** — 완료된 것의 how 는 압축, 합의·미완·제약의 what 은 보존.

## 8. Claude 응답 규칙 (진행 순서대로)

실제 협업 흐름은 조사·진단 → 원칙 합의 → 설계 → 코드 확인 → 코드 제시 → 디스크 반영·커밋 순이다. 아래 규칙도 그 순서를 따른다.

### 8.1. 범위·원칙 고수

- **범위**: MP3 전용이다. 타 포맷 지원 제안은 하지 않는다(무손실 게인은 MP3 `global_gain` 기법이라 원리적으로 타 포맷 적용 불가; 원본 mp3gain 본체도 MP3 전용).
- **원본 동일 재현 + clean-room**: 원본 기능을 임의로 빼거나 단순화하지 않는다(2.1). 무언가를 미루거나 예외로 두려면 먼저 사용자와 합의하고 10 에 명시한다. 사용자가 제공한 원본 C·VB 소스는 사양·동작 이해 목적으로만 읽고 코드를 그대로 옮기지 않는다(2.2). 알고리즘·비트 레이아웃·필터 계수·태그 포맷·UI 동작 같은 공개 사양만 차용해 독립 재작성한다.

### 8.2. 설계·진단이 먼저

코드보다 설계·진단·합의가 앞선다. 코드 블록을 보내기 전 "코드를 보내드릴까요?" 라고 한 박자 묻고, 동의 후 다음 응답에서 제시한다.

### 8.3. 코드 제시 단위

- 변경이 **함수 2개 이하**에서만 일어나고 모듈 최상위를 안 건드리면 → 변경된 함수를 개별 코드 블록으로 **함수 단위 발췌**.
- 그 외(함수 3개 이상·최상위 변경·새 함수·시그니처 변경) → **파일 전체**.
- 어느 경우든 코드 블록 바깥에 변경 지점을 한 문장으로 명시.

### 8.4. 파일 반영은 반드시 코드블록 또는 터미널 명령으로

파일(`.py`·`.md`·`.gitignore` 등)에 반영할 내용은 맨몸 텍스트로 흘려보내지 않고 둘 중 하나로 감싼다.

- **파일 전체 신규·교체** → here-string 터미널 명령: 코드 전체를 `@'` … `'@` 리터럴 here-string 으로 감싸 `| Out-File -FilePath <경로> -Encoding utf8NoBOM` 로 파이프. 사용자가 파일을 직접 열지 않고 VS Code 터미널에 붙여넣어 엔터만 치면 저장되게 한다. (리터럴 here-string 이라 백틱·`$`·따옴표 안전. 단, 코드에 줄 맨 앞이 `'@` 인 줄이 없어야 함 — 제시 전 확인. 마크다운처럼 본문에 코드펜스가 많아 here-string 이 깨질 우려가 있으면, 대신 단일 코드블록으로 전문을 주고 사용자가 파일에 붙여넣게 한다.)
- **국소 수정·삽입/교체 조각** → 코드 펜스로 감싼 발췌. Claude 가 파일 전체 최신본을 정확히 보유하지 못하면 통짜 교체가 다른 부분을 훼손할 수 있으므로, 국소 수정은 통짜 교체보다 조각 발췌를 우선한다. 마크다운 파일의 발췌를 코드블록으로 감쌀 때는 8.6 규칙(안쪽 펜스보다 백틱 하나 더)을 따른다.

### 8.5. 터미널 명령 동봉

파일을 수정·추가·삭제하는 코드를 제시할 때는 디스크 반영·커밋 명령을 같은 응답에 함께 제시. 기본 흐름 ① `git add <파일>` ② `git status` ③ `git commit -m "..."`. (원격 저장소 없으므로 `git push` 생략.) 환경은 PowerShell, cwd=루트. 신규 파일·디렉터리는 `New-Item -ItemType {Directory|File} -Force` 로 만든 뒤 본문을 붙여 넣음 — `-Force` 는 기존 파일을 빈 파일로 덮으므로 한 줄 경고.

### 8.6. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 있으면 바깥 펜스는 안쪽보다 백틱을 하나 더 쓴다(안쪽 3개 → 바깥 4개, 그 안에 또 있으면 5개).

### 8.7. 서식

- 불릿은 `-` + 공백 1칸, 하위 불릿은 부모 기준 2칸 들여쓰기.
- 헤더 번호(1, 1.1 형식, 깊이 2까지)는 **다른 곳에서 참조되는 섹션(2·8·10)에만** 붙인다. 나머지 최상위 섹션은 번호 없이 산문·불릿으로 둔다.
- 과한 볼드·리스트 남용 지양, 산문 우선.

## 9. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 프레임 파서의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함(1·6단계에서 해결·검증 완료).
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain·255-gain 프레임은 클램프로 비가역**: `gain==0` 이면 ±N 으로 안 바뀌고(하한 유지), `gain==255` 에 +N 하면 255 로 클램프되어 초과분이 소실된다(상한). round-trip 완전복원은 경계 프레임이 없거나 경계를 벗어나지 않는 방향으로 적용할 때만 보장된다(원본 `_apply_one` 동작 동일). 통합 테스트의 round-trip 은 상한 255 회피를 위해 음수 스텝 먼저(-3) 후 복원(+3 또는 undo)으로 한다 — ffmpeg 변형 fixture 의 max global_gain 이 255(오른쪽 채널)라 이 방향이 필수.
- **mono 분석 경로 주의(3dB 버그 교훈)**: ffmpeg `-ac 2` up-mix 는 mono 를 각 채널 1/√2 감쇠시켜 라우드니스가 정확히 3dB(≈10·log10 2) 낮게 나온다. mono 는 ffprobe 로 채널 수를 조회해 `-ac 1` 로 원진폭 디코딩 후 코드에서 좌우 복제해야 한다. stereo 위주 검증의 사각지대였음.
- **표시 수식 3건(원본 Mp3Info.cls·DispJunk·AlterDb 대조로 확정)**: (1) **Volume = 89 − raw**(현재 실제 음량, 목표 무관 — 원본 ModifydBGain 상쇄). (2) **적용 후 shift 부호는 하향**: raw 를 `−steps×DB_PER_STEP` 로 낮춘다(원본 AlterDb; `+` 로 하면 Track Gain 이 0 으로 수렴 안 함). (3) **적용 후 peak(curr_max_amp)도 함께 이동**: `×2^(steps/4)` 갱신 후 clip 재판정. 누락하면 목표 왕복 시 curr_max_amp 가 이전 목표값으로 남아 거짓 clip 이 뜬다(원본 exe 실측: 실제 peak 17196 인데 화면 48635). 목표만 바꾸는 `recompute_target` 은 파일 미변경이므로 peak 를 건드리지 않는다.
- **타 포맷 적용 불가**(8.1) / **원본 코드 직접 번역 금지**(2.2) / **원본 기능 임의 축소 금지**(2.1).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 소스는 로컬 보관 + 사용자가 붙여넣어 제공(5). Claude 가 크롤로 가져오려 시도하지 말 것.
- **테스트는 원본 음원을 절대 건드리지 않는다(영구 제약, 오염 사고 재발함)**: 모든 검증·테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다. 각 테스트는 깨끗한 fixture(또는 `-s d` 로 태그 제거한 상태)에서 시작한다. 과거·재발 모두 원본 두 음원에 mp3gain 태그가 남아 테스트가 실패로 보인 사고(코드 결함 아님, 원본 오염 탓). 재발분은 `mp3gain_cli.py -s d` 로 APE 태그 제거해 순수 상태로 복구했다. **원본 경로를 검증 명령에 직접 쓰지 말 것.**
- **undo 0 태그는 남는다(원본 동일 동작)**: 깨끗한 파일에 `-g N` 적용 후 `-u` 하면 오디오 본문은 비트 동일로 복원되지만 `MP3GAIN_UNDO 0,0` APE 태그가 남아 파일 전체 해시는 달라진다. 무손실 검증은 전체 해시가 아니라 tag_offset 까지의 오디오 본문 해시(`audio_body_sha256`)로 판정한다.
- **numpy 배열의 truthiness 평가 금지(앨범 워커 전멸 교훈)**: `arr or []`·`if arr:` 처럼 numpy 배열을 boolean 문맥에 두면 "The truth value of an array with more than one element is ambiguous" 예외가 난다. 앨범 분석 워커에서 `raw.get("histogram") or []` 가 매 곡 이 예외로 죽어 전 곡 실패한 적 있음. 히스토그램 등 배열은 반드시 `x if x is not None else []` 로 판정한다(길이 판단은 `len(x)`, 존재 판단은 `is not None`).
- **초장시간 곡은 통짜 디코딩 금지(메모리 폭증·UI 얼음 교훈)**: 곡 전체 PCM 을 메모리에 올리면(스테레오 10h ≈ 12GB, f64 승격 시 25GB+) 시스템이 스와핑으로 얼어붙고, 파일 경계에서만 취소하면 그 곡이 끝날 때까지 취소가 안 먹힌다. → 분석은 스트리밍(청크 흘림, 10.2), 취소는 청크 경계에서 ffmpeg 즉시 kill.
- **Track Gain 이중 디코딩 금지(이번 세션 해소)**: `apply_track_gain` 은 원래 씨앗 없이 매번 decode+analyze+scan 을 다시 했다. GUI 가 Track Analysis 로 이미 분석한 곡을 Track Gain 하면 같은 디코딩을 한 번 더 해(10h 곡에서 "100% 이후 정지"의 정체) 낭비였다. → `apply_track_gain`/`apply_file_track_gain` 에 씨앗(seed_db_gain·seed_peak·seed_min_gain·seed_max_gain, 또는 api 는 seed dict)을 선택 주입해 유효하면 decode/analyze/scan 을 건너뛴다(결과 수치 동일, 씨앗 없으면 CLI 경로 불변). 씨앗 peak 가 None 이면(태그에 track_peak 없던 경우) 자동으로 디코딩 경로로 폴백(안전).
- **적용 단계도 취소·진행 확인 지점을 가져야 함(취소 갇힘 교훈)**: `scan_gain`·`apply_gain` 은 순수 파이썬 프레임 순회라 디코딩이 없다. 예전엔 여기 취소 확인이 없어 초장시간 곡의 "분석 100% 이후" 순회에 워커가 갇혀 Cancel 이 안 먹고 버튼이 굳었다. → 두 함수에 should_cancel/on_progress 를 `_CALLBACK_INTERVAL`(=4096) 프레임마다 확인, 취소 시 `writer.GainCancelled`(=정상 취소, DecodeCancelled 와 동급). 취소 확인은 파일 write 이전 순회 단계에서만 하므로 취소해도 파일은 원본 그대로(부분 기록 없음). ApplyWorker 는 DecodeCancelled·GainCancelled 를 함께 잡아 정상 종료.
- **255 클램프(비가역)와 클리핑은 별개**: 클램프는 global_gain(8bit)이 255 넘어 잘려 undo 왕복이 깨지는 데이터 손실(9번 상단 항목), 클리핑은 PCM 진폭이 ±32768 넘어 소리가 왜곡되는 청취 품질 문제. 임계값·발생 지점이 달라 한쪽만 생길 수 있다. 클램프는 국소 ~1.5dB 감쇠뿐이라 귀로 거의 판단 불가(문제는 되돌리기 불가), 클리핑은 왜곡음으로 들릴 수 있어 화면 3색 경고. 둘 다 105dB 상한(89 기준 +16dB≈+11스텝)에서도 max_gain 이 높은 곡이면 발생 가능. 원본 mp3gain 은 클램프를 경고 없이 조용히 255 로 자르고 진행(우리 `_apply_one` 동일) — 원본 동일 재현이라 별도 경고 안 함(사전 경고는 원본에 없는 추가 기능이라 MVP 제외).

## 10. 진척 로그 / 정책 / 다음 시작점

### 10.1. 완료 요약 (1~8단계)

**1~7단계 완료·검증 완료. 8단계 GUI MVP 완료(잔여 점검 항목은 10.3).**

1. 프레임 파서 + `global_gain` 읽기/쓰기(`frame.py`·`writer.py`, round-trip 바이트 동일).
2. ReplayGain 분석기(`analysis.py` — equal-loudness 필터+RMS+히스토그램+95퍼센타일−PINK_REF, `db_to_steps`; Track 은 ffmpeg replaygain 과 허용오차 이내, Album 은 44.1k+48k 혼합 검증). 한 48k 곡은 `track_peak>1.0`(1.033) — 클립 방지(-k)에서만 의미, 게인 산출엔 무영향.
3. MP3 디코딩(`decode.py` — ffmpeg/ffprobe subprocess, ±32768 스케일).
4. 태그(`tag.py` APE·`id3.py` ID3v2 — read/write/remove/round-trip, scan_gain, change_gain_and_tag, auto/album 연결, otherFields·Lyrics3/ID3v1 꼬리 보존, useId3 분기).
5. CLI(`mp3gain_cli.py`) — 원본 옵션 전부 재현(직접 게인·분석·적용·클립·database·태그·출력). recalc 비트마스크(FULL/AMP/MIN_MAX)로 디코딩 스킵(결과 수치는 원본 동일). CLI I/O 는 영문만 출력(다국어는 GUI tr() 책임). min/max 스캔 버그 수정: `need_scan = recalc & (FULL|AMP|MIN_MAX)`.
6. 샘플레이트 확장 — 32k / 24k·22.05k·16k / 12k·11.025k·8k 코어 추가·검증. frame.py MPEG2/2.5 분기 실측 재검증(수정 불필요, exe 대조 min/max 전부 일치).
7. 배포 라이선스 1차 점검 — 원본 C 소스와 직접 대조해 전 모듈 clean-room 부합 확인, 도움말 산문 재작성·계수 출처 정직 기재·주석 정리, git 분리 확인, 의존성 매트릭스 정리(numpy·scipy=BSD, PySide6=LGPLv3 동적링크, ffmpeg=외부 호출 전파 없음/동봉 시 LGPL 빌드만). 산출물 `docs/LICENSE_REVIEW.md`.
8. GUI(PySide6, `gui/`) — 파일/폴더 추가·태그 스캔·자연 정렬·다크색상·유니코드·리스트 UX(Delete/더블클릭/고무줄)·Track Analysis(AnalyzeWorker)·Track Gain(ApplyWorker, 원본 RadioGain 재현)·단축키·Clear·취소(청크 경계 즉시 kill)·파일 내부 진행률·스트리밍 분석(수 시간 곡 대응)·창 닫기 안전. 표시값은 원본 exe 실측과 일치(CurrMaxAmp·Volume·Track Gain·clip). `api.analyze_file`(비파괴·무출력)이 CLI --show/GUI/AVD 공유. 대량 추가 성능: 모델에 path→row 딕셔너리 인덱스 도입해 `find_row_by_path` 를 O(1) 로(대량 스캔 O(N²) 제거), 태그 스캔 카운트를 워커 progress 기준으로 통일(읽기 실패 파일 있어도 표시 안 어긋남). 우클릭 팝업(원본 mnuPopup, MVP 4항목: Clear Analysis/Undo/Remove Tags/Play) 추가 — `FileActionWorker`(action="undo"|"remove_tags", 원본 DoFileAction 대응) + `api.undo_file_gain`/`remove_file_tags` 래퍼. 우클릭 시 그 행이 선택에 없으면 그 행만 선택 후 메뉴(원본 "선택 한정" 취지), busy 중 전 항목 비활성.

**검증 인프라.** 통합 테스트 스위트(`tests/`, unittest, 외부 의존 없음) — `python -m unittest discover -s tests` 전부 PASS(118건 기준). 모든 테스트는 원본 음원 불간섭(tempfile 사본, `FixtureGuard` 오염 감시, 무결성은 `audio_body_sha256`). `_support.py`(BaseGainTest·run_cli·해시), 도메인별 test 모듈(roundtrip/analysis/tag/options/recalc/clip/useid3/samplerate/album + GUI 순수 함수부 `test_gui_pure`·스트리밍 동일성 `test_streaming_analysis`). `test_album` 은 그룹핑·스트리밍=벌크 동치·track+album 이중 태그에 더해 `AlbumPeakShiftTest`(앨범 게인 후 태그 peak = `peak_before×2^(steps/4)` = 실제 파형 peak, 89dB 재판정 시 거짓 clip 없음 — 9번 표시 수식 (3)의 앨범 경로 회귀 고정). `test_gui_pure` 는 collect_mp3_paths·모델 path→row 인덱스 불변식·표시 수식(recompute_target/shift_after_apply)을 원본 음원·ffmpeg 없이 검증. `test_streaming_analysis` 는 TrackAnalyzer 스트리밍 누적 = 통짜(analyze_track/track_peak/track_histogram) 결과가 비트 단위 동일함을 여러 청크 크기·샘플레이트로 검증(진척 로그 diff=0 을 정식 고정). fixture 는 Debussy(44.1k)·10cm(48k) 원본 + ffmpeg 변형 다수(mono/stereo·전 샘플레이트). mutagen 상호운용·원본 exe dB 대조는 skip 오염 방지를 위해 `manual_checks/`(git 제외)에서 로컬 수동 실행. exe 는 MSYS2+MinGW-w64(UCRT64)로 빌드한 1.6.2, 사본에 `-o -s s` 로만 정답 추출(원본 오염 방지).

### 10.2. 확정된 정책·결정 (구현 중 새로 정해진 것)

로드맵 단계·2 원칙에 이미 있는 결정(디코더/샘플레이트 예외=2.1)은 여기서 반복하지 않는다. 아래는 작업하며 새로 확정된 사항.

- **저샘플레이트 계수 = 공개 표준값 전사(clean-room 판단)**: 공식 사양(Hydrogenaudio)은 44.1k·48k 계수만 수치로 주고 그 외는 변환만 기술. 원본 동일 응답 재설계는 비공개 equal-loudness target 곡선이 필요하고 scipy 에 MATLAB yulewalk 등가가 없어 원리적으로 막힘(조사 확인). 2.1(원본 동일 재현) 최우선이라 여러 독립 구현에 사실상 사양처럼 공유되는 표준 계수 수치만 차용(코드 독립, 저작권 비대상 수치). 실질 1차 출처는 David Robinson gain_analysis.c 상수(ABYule/ABButter)라는 점을 `analysis.py` docstring·여기에 병기. 44.1k·48k 를 같은 분해 규칙으로 재생성해 자기검증.
- **허용오차 0.1dB(합의)**: 저샘플레이트에서 디코더 차이(mpg123 vs ffmpeg)가 히스토그램 0.01dB 양자화와 맞물려 실측 최대 0.06dB. 2.1 완화가 아니라 디코더가 항구적 예외인 프로젝트에서 불가피 편차의 실측 상한을 정한 것. 계수 오류(수 dB)는 이 기준으로 확실히 걸러짐.
- **표시Only 정책 통일(진척 로그 → 정본)**: `api.analyze_file` 은 원본 DispJunk/Mp3Info.cls 의 Volume·Track Gain·3색 clip 을 재현하되 두 가지 조정 — (1) Track Gain 제수를 화면용 근사 1.505 대신 정밀값 `5*log10(2)=1.50514997831991`(원본도 실제 계산엔 정밀값). (2) 스텝 반올림을 원본 GUI 의 banker's rounding 대신 적용 경로와 동일한 `db_to_steps`(round-half-away-from-zero)로 통일 → "표시된 스텝·dB·clip = 실제 적용 결과" 항상 일치. 0.5dB 경계 극소수 곡에서 원본 GUI 와 1스텝 다를 수 있으나 이것이 우리 적용 결과와 정합하는 올바른 값. clip 판정식(`peak×2^(steps/4)>32767`, 확실/애매 구분)은 저작권 비대상 수식·상수라 차용, VB 폼·이벤트 코드는 미차용.
- **8단계 아키텍처: 코어 직접 import(subprocess 아님)**: 원본 GUI 는 VB↔C 언어차로 exe subprocess 호출·stdout 파싱했으나, 우리는 GUI·코어가 같은 Python 이라 코어 함수를 직접 import(원본 subprocess 는 언어 제약의 산물, 재현 대상 아님 — 재현 대상은 결과·화면 구성·동작). stdout 파싱 취약성 제거, 진행률·취소·에러를 파이썬 객체로, 배포 시 exe 동봉 불필요. 원본 GUI 확증: GUI 는 계산 안 하고 목표 음량을 CLI 인자로 안 넘김(`targetChange` 가 `dblGainAdjust=목표−89` 를 화면 표시용으로만 계산), CLI 는 항상 89 기준 분석·`/g <steps>` 적용, 표시·clip 은 DispJunk 담당.
- **8단계 MVP 범위(합의)**: 컬럼 = 파일명(전체 경로, 원본 Path\File)/Volume/Track Gain/clip(3색: 확실=빨강·애매=파랑·없음=OS팔레트)/Curr Max Amp. 버튼 = Add Files/Folder·Track Analysis(표시만)·Track Gain(적용)·Clear·진행률. 목표 음량은 원본 89dB 기준 그대로 재현하되 "89dB ReplayGain 기준·절대 SPL 아님"을 라벨/툴팁 명시(축소 아님, 표기 명확화). 클립 정책 = auto-clip 끔 + 지정값 그대로 적용 + 판정은 표시로만(원본 mnuDontAddClipping 기본 꺼짐 일치). **MVP 제외(원본에 있으나 후순위)**: Album 계열·Constant Gain·Max No-clip·트레이·로그파일·언어메뉴·정렬 저장. (우클릭 팝업은 이후 구현 완료 — 10.1·10.3 참조.)
- **취소 정책(합의, 갱신됨)**: "파일 경계에서만·진행 중 ffmpeg 방치" → "청크 경계에서 취소·진행 중 ffmpeg 즉시 kill". decode 계층이 청크마다 should_cancel 확인, 서면 proc.kill() 후 DecodeCancelled(=DecodeError 하위) → 워커가 실패 아닌 정상 취소로 구분. 수백 ms 내 반영. 원본 GUI 도 취소 시 exe 종료했으므로 오히려 원본 취소 동작에 더 가까움.
- **스트리밍 분석(곡 전체 PCM 미적재)**: `TrackAnalyzer`(analysis.py) + `decode_pcm_streaming`(decode.py). 청크를 흘려보내며 누적 — 결과는 통짜 처리와 **비트 단위 동일**(diff=0 실측)이라 6단계 exe 대조·0.1dB 검증 불변. 동일성 근거: 필터 lfilter zi 를 청크마다 이어받아 연속 통과, RMS 윈도우 자투리는 버퍼로 이월, peak 는 필터 전 원샘플 abs 최댓값 갱신. 기존 통짜 함수(analyze_track/track_histogram/track_peak, decode_pcm)는 짧은 곡·CLI·테스트용으로 존치. Popen 은 `with proc:` 로 파이프 자동 정리(ResourceWarning 제거).
- **다국어 위치(합의)**: CLI 는 영문만 출력, 화면 표기 다국어화는 PySide6 tr()/번역 파일로 GUI 계층에서 처리(원본 basLocalizer 대응).
- **AVD 연결(확정)**: 병합 시 다운로드 후 별도 단계로 함수 계층(api) 호출(다운로드 파이프라인 실시간 결합 아님). 폴더를 넘기면 곡별 결과 반환.
- **Track Gain 진행바 = 분석 단계 전담(이번 세션 확정)**: 실측상 적용(scan_gain+apply_gain: 디코딩 없는 프레임 순회)은 1시간 곡도 1초 미만으로 전체 소요의 1% 미만, 분석(ffmpeg 디코딩)은 수 분이다. 초기엔 분석0.7/적용0.3 으로 배분했으나 적용이 순식간이라 "70%에서 100%로 툭 점프"해 부자연스러웠고, 0.99 분할도 마지막 1%가 눈에 안 띄었다. → 진행바는 분석 진행률만 0~1 로 표시하고(file_progress), 적용은 on_progress 를 아예 안 넘긴다(진행률 생략). 취소만은 적용 단계에도 should_cancel 로 계속 연결(진행률 뺐다고 취소가 막히지 않음). 미분석 곡은 분석이 0~100% 를 온전히 쓰고 적용은 100% 에서 1초 미만 머문 뒤 완료(가장 정직한 표현). 씨앗 재사용 곡(Analysis 후 Gain)은 분석이 없어 진행바가 잠깐 0 에 머물다 완료(전체 1초 미만).
- **앨범 게인 진행 UI = 2안(이번 세션 확정)**: 앨범 게인은 내부적으로 2단계(분석→적용)다. 진행 표현을 "진행바는 1회, 카운트는 2회 왕복"으로 확정했다. (1) **진행바**는 분석 단계에서만 0→100% 를 한 번 올리고(적용은 프레임 순회라 순식간), 적용 중에는 100% 에 머문다 — Track Gain 진행바 정책(분석 전담)과 동일 사상. (2) **상태바 카운트**는 분석 1/N→N/N, 적용 1/N→N/N 으로 두 번 센다. 카운트는 완료 수가 아니라 현재 처리 곡 번호라 **1 부터 시작**(N 곡이면 N/N 이 끝, `_progress_base + 1` 표시). (3) **문구 구분**: 분석 단계는 "Analyzing", 적용 단계는 "Applying". 두 단계가 슬롯을 공유(`_on_apply_current`/`_on_apply_file_progress`)하므로, `_album_applying` 플래그(적용 진입 시 `_on_album_apply_count` 가 True 로)로 적용 단계 상태바를 `_on_album_apply_count` 에 양보시키고, 분석/적용 문구는 `isinstance(self._worker, AlbumApplyWorker)` 로 갈라 트랙 게인("Applying")과 구분한다. 이 배선으로 이전 세션의 "카운트 0 고정·진행바 튐·24/23 오버슛" 이 모두 해소됐다(상세는 10.3).
- **clear_result 는 tag_scanned 를 유지한다(잘못된 Rescan 제거)**: Rescan 은 대량 추가 시 태그 스캔 Pause→재개 전용이다(분석은 스트리밍이라 이어가기 없음 — 취소 후엔 다시 Track Analysis 가 재개 수단). 예전 `clear_result` 는 tag_scanned 를 False 로 되돌려, 태그 삭제(Remove Tags)·Clear Analysis 후 그 행이 needs_tag_scan()=True 가 되어 의미 없는 Rescan 이 떴다(눌러도 태그 없으니 100% 만 찍고 값 안 나옴). → clear_result 는 result·status 만 리셋하고 tag_scanned=True 유지. 논거: 태그 삭제 결과 = "태그 없는 파일을 추가한 상태"와 동일(tag_scanned=True + 값 없음)이므로, Rescan(태그 읽기) 대상이 아니라 Track Analysis(분석) 대상이어야 한다. status="pending" → needs_analysis()=True, tag_scanned=True → needs_tag_scan()=False.
- **Track Gain steps==0 정책(갱신됨 — 이전 "steps==0 곡 제외"를 폐기)**: Track Gain 은 대상 행을 steps 값과 무관하게 전부 워커에 넘긴다(steps==0 곡도 사전 제외하지 않음). 태그 기록 여부 판단은 코어(`apply_file_track_gain` → `apply_track_gain`)에 맡긴다 — steps==0 이라도 태그가 없거나 오래됐으면(dirty) 코어가 태그를 쓰고(원본 mp3gain `-r` 의 "…but tag needs update" 동작), 이미 최신 태그면 디코딩 없이 `no_change`(tag_written=False)로 넘어간다. `ApplyWorker.run` 도 steps==0 단축 경로를 제거하고 항상 `apply_file_track_gain` 을 호출한 뒤 코어 status(ok→row_applied / no_change→row_analyzed / 그외→failed)로만 분기한다. **폐기 사유**: 구버전은 GUI(`_on_gain`)가 result.steps==0 곡을 대상에서 사전 제외하고 워커의 steps==0 도 apply 를 건너뛰어, 태그 삭제 후 이미 목표 볼륨인 곡의 dirty 태그가 안 써지는 버그가 있었다(태그 삭제→분석→Track Gain 시 재현). GUI 행 status 로는 태그 존재 여부를 구분할 수 없다(태그 삭제 후 분석한 행도 status=analyzed)는 점이 사전 제외를 불가능하게 하는 근거. 트레이드오프: steps==0 곡도 워커를 거쳐 태그를 한 번 재확인하는 비용이 생기나, 태그가 있으면 코어가 디코딩을 생략해 가볍다.
- **8단계 GUI 세부 재현 메모(원본 폼 대조)**: NAME 은 전체 경로 표시. 자연 정렬(QCollator numericMode, 미분석 None 은 항상 뒤). 다크테마 안전 색상(none 은 OS 팔레트 위임). 플랫폼 폰트(Win 만 Segoe UI Variable Text, QFontInfo 확인 후). 유니코드 파일명 완전 지원(원본 VB6 ANSI 한계 개선). Delete 키=선택 삭제, Clear 버튼/Ctrl+Shift+Delete=전체 삭제(원본 ClearFiles/ClearAll 2분리), 더블클릭=기본앱 재생, 빈 영역 고무줄 선택(QTableView 직접 구현). 추가 시 태그 동기 스캔(`read_file_tags`, 곡당 ~1ms) + 대량 추가는 `TagScanWorker` 백그라운드(겸용 버튼: 스캔 중=Pause·분석/게인/액션 중=Cancel·pending 있으면=Rescan). Track Analysis 대상="선택 있으면 선택·없으면 전체" 중 값 없는 행만. Track Gain 은 대상 행을 steps 무관 전부 워커에 넘김(steps==0 제외 안 함, 위 정책 참조). Track Analysis 는 태그 미기록(원본 `/o` 출력전용 확증), 기록은 Track Gain(`/g` changeGainAndTag)뿐. 우클릭 팝업: `contextMenuEvent`→`context_menu_requested`→`_show_context_menu`, 우클릭 행이 선택에 없으면 그 행만 선택. Undo 성공 시 `shift_after_apply(result, undo_steps)`로 표시 복귀, Remove Tags 성공 시 `clear_result`로 미분석 복귀. 단축키 Add Files=Ctrl+F·Folder=Ctrl+D·Analysis=Ctrl+T·Gain=Ctrl+G(원본 메뉴 재현). 파일 내부 진행률은 duration 기반 예측 바이트 대비 누적 비율, 진행바 세분 합산(_PROGRESS_SCALE=1000). 창 닫기 시 워커 request_cancel→wait(10s).

### 10.3. 현재 상태 · 완료 이력 · 다음 할 일

**현재 상태.** 1~7단계 완료, 8단계 GUI MVP + Track/Album 계열 모두 실사용 완료. HEAD=`c83b9f1`. GUI 는 Track 분석/게인, Album 분석/게인, 우클릭 팝업, 취소, 스트리밍까지 실사용 가능하다. 메뉴바(File/Analysis/Modify/Options)와 툴바가 같은 QAction 을 공유한다. 단축키: Track Analysis=Ctrl+T·Track Gain=Ctrl+G·Album Analysis=Ctrl+U·Album Gain=Ctrl+B. 진행 UI 는 2안 확정(진행바 1회 0→100%, 카운트 분석/적용 2회 왕복 1..N, 문구 Analyzing→Applying — 상세 10.2). 통합 테스트 118건 전부 PASS. 후순위 GUI 항목 중 컬럼폭·정렬 상태 저장을 완료했다(창 기하·컬럼폭·정렬을 QSettings("GaindB","GaindB")로 영속화, 원본 ListView 처럼 전 컬럼 Interactive + 넘치면 가로 스크롤, Reset Column Widths 액션=원본 mnuResetColumns, 선택 하이라이트가 컬럼 경계 없이 행 전체로 이어짐 + 헤더 border-right 세로 구분선, 최초 실행 시 전 컬럼 default_width 합계 기준 초기 창 폭 자동).

**완료 이력(커밋순).**
- `e82a79a` feat: 앨범 게인 코어 경로(공유 본체 `_apply_one_album_file` + 스트리밍 api 레이어).
- `5735bcc` fix: api 앨범 import 를 공유 `_apply_one_album_file` 로 정렬.
- `a068cc1` test: 앨범 코어 검증(`tests/test_album.py` — 그룹핑, 스트리밍=벌크 비트 동치, track+album 이중 태그).
- `99a5ecc` feat: 리스트뷰 앨범 3컬럼(`columns.py` ALBUM_VOLUME/ALBUM_GAIN/ALBUM_CLIP, COLUMN_COUNT=8, model.py 표시·정렬·전경색 확장).
- `1b205e7` feat: 앨범 analyze/apply 워커 + raw→display api 헬퍼(`AlbumAnalyzeWorker`·`AlbumApplyWorker`·`result_from_album_raw`).
- `d805095` fix: 앨범 게인 진행 UI(진행바 1회·카운트 2회 왕복·Analyzing/Applying) + step 4 메인윈도우 배선. 이 과정에서 앨범 관련 버그 5건 해소: (1) histogram numpy 배열 truthiness ValueError 로 전 곡 사망(→ `is not None` 판정, 9번 함정 등재), (2) 진행바 튐(→ `_progress_base` 단일화), (3) 상태바 카운트 0 고정·1부터 시작(→ 진행 신호 기반 현재 곡 번호), (4) 앨범 게인 분자 24/23 오버슛(→ `_album_applying` 플래그로 적용 단계 상태바 양보), (5) 씨앗 있어도 항상 재분석(→ `_ensure_group_raws` 가 `_album_raws` 씨앗 히트 시 재분석 생략, 원본 앨범 모드처럼 볼륨 알면 바로 적용).
- `f59b1b2` chore: 진단 DEBUGLOG 제거(`gui/workers.py`·`gui/main_window.py`, 이전 세션 `d805095` 에 임시 삽입했던 `_dlog` 전량 삭제).
- `ce5c18c` docs: `_on_apply_analyzed` docstring 을 no_change 정책에 맞게 정정(옛 steps==0 제외 흔적 제거).
- `da5ecf6` test: 앨범 게인 후 peak 이동 검증(`AlbumPeakShiftTest`). **결론: 앨범 peak 이동은 트랙·앨범이 공유하는 `change_gain_and_tag`(left==right 일 때 track/album peak 둘 다 x2^(steps/4))가 구조적으로 보장한다.** 이전 세션에서 의심됐던 "앨범 게인 후 트랙 게인 클리핑"은 peak 계산 결함이 아니라 표시·배선 층 문제였고 앨범 경로 정상화로 해소됐음이 확증됨(회귀 테스트로 고정). — 이 항목으로 이전 "현재 재현 안 됨" 미결이 종결됨.
- `c83b9f1` feat(gui): 컬럼폭·정렬·창 기하 QSettings 영속화 + 리셋 액션 + 선택 하이라이트 이어짐 + 헤더 세로 구분선 + 초기 창폭 자동. 저장 키: `window/geometry`·`columns/width_N`(+스키마 방어 `columns/count`)·`sort/column`·`sort/order`(정렬 저장은 원본에 없는 확장). 전 컬럼 Interactive + `setStretchLastSection(False)`로 원본 ListView 동작(드래그 경계만 이동, 넘치면 가로 스크롤). `ColumnDef.default_width` 신설, `_reset_column_widths`(원본 mnuResetColumns)로 복원. `_TABLE_QSS` 스타일시트로 셀 테두리 제거(선택 하이라이트 행 전체 이어짐)·`QHeaderView::section` `border-right`로 세로 구분선 유지. `_default_window_size` 로 최초 실행 시 default_width 합계 기준 창 폭 자동(저장 geometry 있으면 그대로 복원). 세로선이 안 보이면 `palette(mid)` 대비 문제이므로 고정색(라이트 `#b0b0b0`/다크 `#5a5a5a`)으로 교체.

**다음 할 일(남은 것만).**

- **후순위 기능 GUI(착수 시 해당 원본 폼 붙여 제공).**
  - 트레이·로그파일·언어메뉴(원본 basLocalizer 대응, tr()/번역파일). (컬럼폭·정렬 상태 저장은 `c83b9f1` 로 완료.)
- **실클릭 회귀 — 해시 무결성만 남음(반복 점검).** 취소 후 파일 원본 무결성을 `audio_body_sha256` 로 실측 비교. GUI 를 건드릴 때마다 재확인하는 체크리스트로 존치.
- **보류·점검 항목(성격이 각각 달라 완료로 옮기지 않고 존치).**
  - **비가역(255 클램프) 사전 경고 — 보류 확정(합의).** 원본은 경고 없이 조용히 클램프(원본 동일 재현)라 사전 경고는 원본에 없는 추가 기능. 재론하려면 원본 이탈 감수 가치의 사용자 합의 필요.
  - **steps==0 곡의 태그 재확인 비용 — 유효성 재확인, 최적화 보류.** 태그가 있으면 코어가 디코딩 생략해 가벼움. 체감 지연 시 모델 `has_tag` 플래그로 최신 태그 곡만 사전 제외 최적화 고려.
  - **Constant Gain(`-g`/`-l 0`/`-l 1`) GUI — 최후순위 보류(합의, 축소 아님).** 코어(`apply_gain`) 완비, 슬라이더 다이얼로그+워커만 얹으면 됨. 재개 시 4개 논점 합의 필요(태그 갱신 경로·채널별 옵션·진행률 정책·UI 위치).
  - **Max No-clip(`-x` 계열) GUI — 보류(합의, 축소 아님).** 계산 뼈대는 `-k`(autoClip) 로 코어에 존재. peak≠라우드니스 부작용 + 원본조차 기본 숨김(mnuMaxAmp.Visible=False). 앨범 그룹 버전은 Album 폴더 그룹핑 인프라 재사용이라 착수 수월.
- **CLAUDE.md 유지.** 단계 완료 시 본 10.3 만 갱신(완료 이력에 커밋 한 줄 추가, 끝난 항목은 다음 할 일에서 제거). 2 핵심 원칙을 약화시키는 압축은 금지(2·8 참조).
