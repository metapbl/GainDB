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
  - **샘플레이트(확장 완료)**: 실제 음원 다수인 44.1k·48k 를 먼저 구현·검증한 뒤, ReplayGain 사양의 나머지 샘플레이트(32k 및 MPEG2/2.5 계열)까지 확장·검증 완료. 계수는 공개 표준값 전사(재설계 불가 사유·clean-room 판단은 10 로그).

### 2.2. clean-room 전면 적용

이 프로젝트의 **모든 구성 요소**는 clean-room 으로 작성한다 — 코어(`gaindb/`)·CLI 는 물론, 앞으로 추가될 GUI(8단계)와 그 이후 어떤 확장이든 예외 없이 적용된다. 원본 MP3Gain 의 어떤 코드(C 본체든 VB GUI 든)도 직접 번역·복붙하지 않는다. 다른 언어로 옮기는 것도 2차적 저작물이므로 금지한다. 우리가 차용하는 것은 **저작권 대상이 아닌 것** — 알고리즘, 파일·태그 포맷, 비트 레이아웃, 필터 계수 수치, 옵션 체계, 화면 구성·동작 같은 공개 사양과 관찰된 동작뿐이다. 그 위에서 결과(동작·포맷·출력·외관)는 원본과 일치시키되 코드는 독립 작성한다. 원본 소스(C·GUI 모두)는 사양·동작 이해 목적의 참고 자료로만 로컬 보관하며 git 에서 제외한다(LGPL 분리).

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
- **GUI(8단계 예정)**: PySide6 (Qt for Python, LGPL). Windows·macOS 크로스플랫폼. AVD 프로젝트와 스택 일치(향후 병합 대비). 기존 `gaindb/` 코어 + CLI 위에 얹는 새 프런트엔드(코어 재작성 없음).
- **가상환경**: venv (`.venv`).

루트: `C:\Users\ggoyo_zhxlvdr\GaindB` (구조가 바뀌면 이 트리와 10 진척 로그를 함께 갱신한다.)

````
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
````

`mp3gain/` 하위 전체는 git 제외 — 원본 C·GUI 소스, 빌드 산출물 `mp3gain.exe` 모두 LGPL 분리 대상. exe 는 코드가 아니라 실행 결과만 검증 기준으로 쓰므로 clean-room 위반이 아니다(2.2 의 "관찰된 동작 차용").

## 5. 원본 참고 자료 · 새 세션 시작법

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `mp3gain/src/` 에 보관**(master.zip 압축 해제본). LGPL 분리를 위해 git 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- **원본 Windows GUI(MP3GainGUI)는 VB 로 작성된, CLI `mp3gain.exe` 를 호출하는 프런트엔드**다. 소스를 로컬 `mp3gain/mp3gain-win-gui-1_3_4-src/` 에 보관(git 제외). 8단계에서 화면 구성·동작을 관찰·참고하되 코드는 옮기지 않는다(2.2). 공식 출처: SourceForge mp3gain 의 `mp3gain-win-gui-1_3_4-src.zip`.
- **이 미러의 `.c` 는 크롤 불가**(`application/octet-stream` MIME). 그래서 C·VB 소스는 로컬 보관 + 사용자가 붙여넣어 제공. Claude 가 크롤로 가져오려 시도하지 말 것.
- **새 세션 시작**: 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다(`CopyClaudeMd.bat` 실행 → 채팅 입력창에 Ctrl+V). 이어 그 세션 단계에 필요한 소스(.c/.h 또는 GUI)를 붙여넣어 제공한다. 검색 도구는 최신 정보 확인용으로만 쓰고, 원본 소스 입수에는 쓰지 않는다.

## 6. 구현 단계 로드맵

> 아래 단계는 작업을 나누기 위한 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다**(2.1).

1. **[완료] MP3 프레임 파서 + `global_gain` 읽기/쓰기** — 순수 Python. 읽기·쓰기·무손실 round-trip 검증 완료.
2. **[완료] ReplayGain 분석기** (numpy/scipy) — equal-loudness 필터 + RMS + 통계, Track/Album gain, dB→스텝 변환. 44.1k·48k 검증(나머지 샘플레이트는 6단계 확장).
3. **[완료] MP3 디코딩(PCM 추출)** — ffmpeg/ffprobe subprocess(`gaindb/decode.py`).
4. **[완료] 태그 처리** — APEv2 읽기·쓰기·갱신·제거, scanFrameGain(min/max), changeGainAndTag 동등, undo, auto/album 연결. otherFields·Lyrics3/ID3v1 꼬리 보존. ID3v2(RVA2/TXXX) 포함.
5. **[완료] CLI / 옵션 / 일괄 처리** — 원본 옵션을 빠짐없이 재현(`-r`/`-a`/`-e`/`-g`/`-l`/`-d`/`-m`/`-k`/`-c`/`-w`/`-s c|d|s|r|u|i|a`/`-u`/`-o`/`-q`/`-p`/`-x`/`-f`/`-t`/`-T` 등), 클리핑 경고·자동 클립(`-k`), database 출력(`-o`) 포함. 통합 테스트 스위트로 검증.
6. **[완료] 샘플레이트 확장 (원본 동일 재현 완결)** — 44.1k·48k 외 ReplayGain 사양 전 샘플레이트(32k / MPEG2·MPEG2.5 계열)를 코어에 추가·검증. 계수는 공개 표준값 전사(자체 재설계는 비공개 target 곡선으로 불가 — 상세 10), frame.py MPEG2/2.5 파싱 실측 재검증(수정 불필요), mono 분석 3dB 버그 발견·수정, MPEG2/2.5 fixture·테스트 편입.
7. **[완료] 배포 라이선스 정합성 준비·검토** — 배포 대비 LGPL 구속 회피 근거 정리·점검. (a) clean-room 자체 점검: 코어·CLI·GUI 어디에도 원본 C·VB 코드가 옮겨지지 않았고 결과 일치·코드 독립임을 확인(2). (b) 배포 시 검토 항목: PySide6(LGPL) 링크 방식, ffmpeg 동봉 여부(GPL), 원본 소스 git 제외 상태 등. GPT·Claude 최신 모델 교차검증으로 1차 수행. **실제 공개 배포 직전의 최종 확인은 자격 있는 전문가(변호사) 검토를 남겨둔다 — AI 교차검증은 1차 수단일 뿐 법적 책임·자격을 대체하지 못한다(2.3). 로컬 개인 사용 단계에서는 불필요.**
8. **[7단계 후] GUI (PySide6, clean-room 재현)** — 원본 MP3GainGUI 의 외관·기능·동작을 PySide6 로 동일 재현하되 VB 코드를 옮기지 않고 공개 동작만 보고 독립 구현(2). 기존 코어 + CLI 위에 얹는 새 프런트엔드(코어 재작성 없음). Windows·macOS 크로스플랫폼. **세부 MVP 설계(화면·버튼·옵션 구성·순서)는 착수 전 사용자와 합의해 정한다**(2.1). 원본 GUI 소스는 **VB6**(`.vbp`/`.frm`/`.frx`/`.bas`/`.cls`). 구성(관찰): 메인 창(`frmMain`)·옵션(`frmOptions`)·게인 입력(`frmGetGain`)·로그(`frmLogs`)·시스템 트레이(`frmSysTray`)·정보/기부/면책 다이얼로그, 경고 모달들(`frmStereoWarning`=단일채널 거부, `frmLayerCheckWarning`=Layer 오인, `frmSkipTagsWarn`/`frmReadOnly`/`frmResetWarn` 등); 모듈 `basLocalizer`(다국어)·`basSaveAnalysis`·`basListViewSort`·`Mp3Info.cls` 등. 다수 경고 폼은 CLI 가 이미 동작으로 재현한 상황의 GUI 대응 — 이 매핑을 PySide6 다이얼로그로 재현(화면·동작 관찰만, 복붙 금지). **다국어(한국어·영어)는 GUI 계층의 책임(합의됨): CLI 는 영문만 출력하고, 화면 표기의 다국어화는 PySide6 의 tr()/번역 파일로 GUI 에서 처리한다**(원본 basLocalizer 대응).
   - **아키텍처 합의(8단계 착수 전 확정, 코어 직접 import — subprocess 아님)**: 원본 GUI 는 VB↔C 언어 차이 때문에 exe 를 subprocess 호출하고 stdout 을 파싱했으나, 우리는 GUI(PySide6)·코어(gaindb)가 같은 Python 이므로 **코어 함수를 직접 import** 한다(원본의 subprocess 방식은 언어 제약의 산물일 뿐 재현 대상이 아님 — 재현 대상은 결과·화면 구성·동작). 이로써 stdout 파싱 취약성 제거, 진행률·취소·에러를 파이썬 객체로 처리, 배포 시 exe 동봉 불필요. **8단계 첫 하위작업 = 순수 함수 API 계층 분리**: `_run_analysis` 등에 print 와 뒤섞인 계산 로직을, 파일 하나를 받아 결과 객체(track_db·steps·peak·min/max_gain·clip_state 등)를 반환하는 순수 함수로 분리한다(코어 재작성이 아니라 print↔반환값 분리 리팩터링, 원본 재현 불변). CLI·GUI·AVD 셋이 이 함수 계층을 공유한다.
   - **MVP 범위 합의**: 컬럼 = 파일명 / Volume(예측 결과 dB, 재분석 없이 `목표 − RadiodBGain` 계산) / Track Gain(적용 dB, `steps × 5log10(2)`) / clip(확실=빨강·애매=파랑·없음 3색, 원본 DispJunk 재현) / Curr Max Amp(클립 근거). 버튼 = Add Files/Folder · Track Analysis(적용 없이 표시만) · Track Gain(적용) · Clear · 진행률. **MVP 제외(원본에 있으나 후순위)**: Album 계열·Constant Gain·Max No-clip("Maximizing")·시스템 트레이·로그파일·언어메뉴·정렬. 목표 음량은 원본 동작(89dB 기준 offset) 그대로 재현하되 **"89dB ReplayGain 기준이며 절대 SPL 이 아님"을 라벨/툴팁에 명시**(기능 축소 아님, 표기 명확화). 클립 정책은 **auto-clip 끔 + 지정값 그대로 적용 + 판정은 표시로만**(원본 mnuDontAddClipping 기본 꺼짐과 일치). clip 판정식(`peak×2^(steps/4)>32767`, 확실/애매 구분식·`1.505` 등)은 저작권 비대상 수식·상수라 차용, VB 폼·이벤트 코드는 옮기지 않음(관찰된 동작만 독립 구현).
   - **AVD 연결 방식(확정)**: AVD 병합 시 **다운로드 후 별도 단계**로 위 함수 계층을 호출(다운로드 파이프라인 실시간 결합 아님). 폴더를 넘기면 곡별 결과 반환.


## 7. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell 7.6.3). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만. (GUI 8단계는 macOS 동작도 목표.)
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits(`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: `>` 리다이렉션은 UTF-16 LE BOM 으로 쓴다. 파일 쓰기는 `... | Out-File -Encoding utf8NoBOM <파일>` 로 BOM 없는 UTF-8 을 명시한다(7.x 는 `utf8` 도 기본 BOM 없음이지만 `utf8NoBOM` 으로 통일).
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
- `##`/`###` 헤더에 1, 1.1 형식 번호(깊이 2까지).
- 과한 볼드·리스트 남용 지양, 산문 우선.

## 9. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 프레임 파서의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함(1·6단계에서 해결·검증 완료).
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain·255-gain 프레임은 클램프로 비가역**: `gain==0` 이면 ±N 으로 안 바뀌고(하한 유지), `gain==255` 에 +N 하면 255 로 클램프되어 초과분이 소실된다(상한). round-trip 완전복원은 경계 프레임이 없거나 경계를 벗어나지 않는 방향으로 적용할 때만 보장된다(원본 `_apply_one` 동작 동일). 통합 테스트의 round-trip 은 상한 255 회피를 위해 음수 스텝 먼저(-3) 후 복원(+3 또는 undo)으로 한다 — ffmpeg 변형 fixture 의 max global_gain 이 255(오른쪽 채널)라 이 방향이 필수임이 통합 테스트에서 실증됨. (적용된 파일을 재계산하면 적용분이 반영된 "현재 상태"의 min/max·dB 가 나오는 것이 정상.)
- **타 포맷 적용 불가**(8.1) / **원본 코드 직접 번역 금지**(2.2) / **원본 기능 임의 축소 금지**(2.1).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 소스는 로컬 보관 + 사용자가 붙여넣어 제공(5). Claude 가 크롤로 가져오려 시도하지 말 것.
- **테스트는 원본 음원을 절대 건드리지 않는다(영구 제약, 오염 사고 교훈)**: 모든 검증·테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다. 각 테스트는 깨끗한 fixture(또는 `-s d` 로 태그 제거한 상태)에서 시작한다. 과거 옛 verify_*.py 가 원본 두 음원에 mp3gain 태그를 남겨 round-trip 해시가 어긋나 보이는 사고가 있었다(코드 결함 아님, 원본 오염 탓). 두 음원은 순수 상태로 복구함.
- **undo 0 태그는 남는다(원본 동일 동작)**: 깨끗한 파일에 `-g N` 적용 후 `-u` 하면 오디오 본문은 비트 동일로 복원되지만 `MP3GAIN_UNDO 0,0` APE 태그가 남아 파일 전체 해시는 달라진다(원본 changeGainAndTag 의 "don't remove it"). 무손실 검증은 전체 해시가 아니라 tag_offset 까지의 오디오 본문 해시로 판정한다.
- **적용 후 표시 갱신은 peak(curr_max_amp)도 함께 이동해야 한다(clip 정합의 핵심)**: `shift_after_apply` 는 원본 `AlterDb` 의 세 갱신을 모두 재현해야 한다 — raw track_db 하향(`-steps×DB_PER_STEP`), **peak `×2^(steps/4)` 갱신**, 그에 따른 clip 재판정. peak 갱신을 빠뜨리면 목표를 올렸다 내렸다 할 때 curr_max_amp 가 이전 목표의 값으로 남아 clip 표시가 실제 파일과 어긋난다(원본 exe 대조로 실증: 실제 peak 17196 인데 화면엔 48635·거짓 clip). 목표만 바꾸는 `recompute_target` 은 반대로 peak 를 건드리지 않는다(파일 미변경이므로).

## 10. 진척 로그 / 다음 세션 시작점

**1~6단계 완료·검증 완료.**

1) 프레임 파서 + `global_gain` 읽기/쓰기(`gaindb/frame.py`·`writer.py`, round-trip 바이트 동일). 2) ReplayGain 분석기(`gaindb/analysis.py` — equal-loudness 필터+RMS+히스토그램+95퍼센타일−PINK_REF, `db_to_steps`; Track 은 ffmpeg replaygain 과 허용오차 이내, Album 은 44.1k+48k 혼합 검증). 3) MP3 디코딩(`gaindb/decode.py` — ffmpeg/ffprobe subprocess, ±32768 스케일). 4) 태그(`gaindb/tag.py` APE·`gaindb/id3.py` ID3v2 — read/write/remove/round-trip, scan_gain, change_gain_and_tag[undo 누적·gain 차감·peak ×2^(N/4)·minmax], auto/album 연결, otherFields·Lyrics3/ID3v1 꼬리 보존, useId3 분기).

- **48k 관찰**: 한 테스트 곡 `track_peak>1.0`(1.033) — 클립 방지(-k)에서 의미, 게인 산출엔 무영향.

**5단계 (CLI / 옵션 / 일괄 처리).** `mp3gain_cli.py` — 원본 옵션을 빠짐없이 재현(직접 게인 `-g`/`-l`/`-u`, 분석·적용 `-r`/`-a`/`-e`/`-x`/`-m`/`-d`, 클립 `-k`/`-c`, database `-o`, 태그 `-s c|d|s|r|u|i|a`, 출력·동작 `-t`/`-T`/`-q`/`-p`/`-f`/`-w`/`-v`/`-h`/`-?`). recalc 비트마스크(FULL/AMP/MIN_MAX)로 디코딩 스킵(디코더 예외의 귀결) — 결과 수치는 원본 동일, 디코딩 횟수만 다름. curAlbum 비교는 원본대로 부동소수 정확 일치(epsilon 미도입, 합의됨). 개발용 CLI 는 `--debug-scan`/`--debug-tag` 로 흡수. CLI I/O 는 영문만 출력(다국어는 GUI tr() 책임 — 합의됨); docstring·주석만 한국어.

**통합 테스트 스위트 (tests/, unittest, 외부 의존 없음).** `python -m unittest discover -s tests` 로 실행·전부 PASS. 옛 verify_*.py 8개를 대체·흡수하고 삭제. 모든 테스트는 원본 음원 불간섭 — tempfile 사본에서만 동작, `FixtureGuard` 가 원본 해시로 오염 감시, 무결성 판정은 `audio_body_sha256`(프레임 구간; 태그 생성·undo 0 잔존과 무관). 구성:

- `_support.py` — REPO_ROOT/MP3_DIR(환경변수 `GAINDB_TEST_MP3_DIR` 우선), `KNOWN_FIXTURES`, `BaseGainTest`(사본·가드·`run_cli`[subprocess, UTF-8 강제]·`audio_body_sha256`).
- `test_support_smoke`(3) / `test_roundtrip_options`(9) / `test_analysis_integration`(6) / `test_tag_integration`(7) / `test_options_parsing`(9) / `test_recalc_decode_skip`(5) / `test_cli_misc`(11+2 회귀) / `test_clip_integration` / `test_useid3_migration`(4) / `test_samplerate_expansion`(24). (전체 86건 PASS 기준; 개별 건수 표기는 근사.)
- **verify_* → 통합 스위트 매핑**: cli_ab→options_parsing+roundtrip/tag, c1→analysis+cli_misc, c2→analysis/tag+cli_misc, c3→clip+cli_misc, d1→tag+cli_misc, d2→recalc_decode_skip, 5c→useid3_migration.
- **mutagen 상호운용·exe 대조는 통합 스위트 밖(합의됨)**: 외부도구 상호운용·정답지 대조는 mutagen/exe 부재 환경 skip 오염을 피해 `manual_checks/`(git 제외)에 로컬 보존·수동 실행.

**테스트 fixture (ffmpeg 변형, git 제외·합의됨 2.1)**: Debussy(44.1k)에서 채널 모드 커버리지용 생성 — mono `test_mono_44k.mp3`, stereo `test_stereo_44k.mp3`(둘 다 MPEG1·44100·CRC=no, max global_gain=255 포함, R 채널). 6단계 확장 fixture 9개는 아래 참조. 원본 음원(Debussy 44.1k·10cm 48k)은 mp3gain 태그 없는 순수 상태(128바이트 ID3v1 꼬리만). 통합 테스트는 전부 tempfile 사본에서 시작.

**검증 기준 exe 확보 + min/max 스캔 버그 수정.** 6단계 계수 검증 정답지로 쓸 원본 mp3gain 1.6.2 CLI 를 MSYS2+MinGW-w64(UCRT64)로 빌드. 절차: MSYS2 설치 → `pacman -S mingw-w64-ucrt-x86_64-{gcc,make,mpg123,pkgconf}` → UCRT64 창에서 `mp3gain/src` 로 이동해 `gcc -O2 -include windows.h -o mp3gain.exe mp3gain.c gain_analysis.c apetag.c id3tag.c rg_error.c -lmpg123 -lm`. (`-include windows.h` 는 MSVC 전제 보완. MMSYSERR 중복정의 경고 무해.) 정답은 사본에 대해 `./mp3gain.exe -o -s s <사본>` 으로 뽑는다(원본 오염 방지 위해 반드시 사본·`-s s`). Debussy(44.1k): exe dB=0.69 / GaindB dB=0.71 → 같은 기준 확인, 정답지로 신뢰 가능.

- **min/max 스캔 버그 수정(커밋 d8b44cc·회귀 ce18b53).** exe 는 `-s s` 에서도 min/max global_gain 을 출력하는데 GaindB 는 0/0 이었다. 원인: `_analyze_one` 의 scan 이 `MIN_MAX_GAIN_RECALC` 비트에만 묶여 그 비트 없는 recalc 경로(-s s 는 FULL, -x 는 AMP)에서 누락. 수정: `need_scan = recalc & (FULL|AMP|MIN_MAX)`(recalc 0 이면 여전히 스킵). 회귀 테스트 `MinMaxScanRegressionTest` 추가.

**6단계 완료·검증 완료 (샘플레이트 확장 — 원본 동일 재현 완결).** 44.1k·48k 외 ReplayGain 사양 전 샘플레이트(32k / 24k·22.05k·16k / 12k·11.025k·8k)를 코어에 추가·검증. 2.1 의 "샘플레이트 합의된 미완"이 이로써 해소됨.

- **계수 전사 결정(합의됨, clean-room 판단 명시).** 저샘플레이트 필터 계수는 자체 재설계가 아니라 공개 표준 계수를 사양 데이터로 전사. 사유: 공식 사양(Hydrogenaudio)은 44.1k·48k 계수만 수치로 제공하고 그 외는 "coefficients must be transformed"라고만 기술한다. 원본과 동일 응답을 재설계하려면 비공개인 equal-loudness target 곡선이 필요하고 scipy 에 MATLAB yulewalk 등가도 없어 재설계 경로가 원리적으로 막힘(조사로 확인). 2.1(원본 동일 재현) 최우선이므로 여러 독립 구현에 사실상 사양처럼 공유되는 표준 계수 수치만 차용(코드는 독립, 저작권 대상 아닌 수치 데이터). 실질 1차 출처가 David Robinson gain_analysis.c 상수라는 점은 `analysis.py` docstring 과 여기에 병기. 44.1k·48k 를 같은 분해 규칙으로 재생성해 기존 검증값과 일치 확인(자기검증), 7개 전부 표준값과 자릿수 대조 통과.
- **frame.py MPEG2/2.5 실측 재검증 완료(파서 1단계 난점 해소).** `_read_global_gains` 의 MPEG2/2.5 분기(granule 1, private bits 1/2)를 9개 fixture 로 parse_file 검증 — 버전·샘플레이트·nchan·gains 개수(frames×granule×nchan)·정상 분포 확인, exe 대조에서 min/max global_gain 9개 전부 정확 일치. frame.py 수정 불필요로 확정.
- **mono 분석 3dB 버그 발견·수정(커밋 68493a9).** exe 대조에서 mono fixture 만 정확히 3.05dB(≈10·log10 2) 어긋남. 원인은 계수가 아니라 `decode.py`: ffmpeg `-ac 2` up-mix 가 mono 를 각 채널 1/√2 감쇠(ratio=√2 실측) → `(lsum+rsum)*0.5` 가 원본의 절반. 수정: ffprobe 로 채널 수 조회해 mono 는 `-ac 1` 로 원진폭 디코딩 후 코드에서 좌우 복제. 기존 검증이 stereo 위주라 사각지대였던 mono 경로 버그. 수정 후 diff 3.05→0.04.
- **허용오차 0.1dB 로 상향(합의됨).** 기존 "0.02dB 이내"를 0.1dB 로 조정. 사유: 저샘플레이트에서 디코더 차이(mpg123 vs ffmpeg)가 히스토그램 0.01dB 경계 양자화와 맞물려 실측 최대 0.06dB(32k 0.03, 24k 0.06). 2.1 "결과 일치" 완화가 아니라, 디코더가 항구적 예외(2.1)인 프로젝트에서 디코더 차이로 인한 불가피 편차의 실측 상한을 정한 것. 계수 오류(수 dB)는 이 기준으로 확실히 걸러짐.
- **검증 인프라.** 새 fixture 9개(`test_{32k,24k,22k,16k,12k,11k,8k}.mp3`, `test_mono_{24k,12k}.mp3` — Debussy 에서 ffmpeg 변형, git 제외, `.gitignore`·`KNOWN_FIXTURES` 등록). 통합 스위트에 `test_samplerate_expansion.py` 추가(24건: FrameParse 9 / RoundTrip 6 / Analysis 9) → 전체 86건 PASS(커밋 04b9818). exe dB 정답 대조는 `manual_checks/compare_exe_lowrate.py`(git 제외, 로컬 수동). exe 실행은 VS Code 터미널에서 `$env:PATH="C:\msys64\ucrt64\bin;"+$env:PATH` 후 가능(MinGW DLL 경로).

찾기:
**다음 = 7단계 배포 라이선스 정합성 준비·검토.** 1~6단계 완료(코어의 원본 재현 완결). 7단계: 배포 대비 clean-room 자체 점검(코어·CLI·GUI 어디에도 원본 C·VB 코드가 옮겨지지 않음 확인) + LGPL 구속 회피 근거 정리(PySide6 링크 방식, ffmpeg 동봉 여부, 원본 소스 git 제외 상태), AI 교차검증 1차 + 전문가 최종 확인. 로컬 개인 사용 단계에서는 불필요(2.3). 그다음 8단계 GUI(PySide6, clean-room 재현, MVP 설계는 착수 전 합의).

바꾸기:
**7단계 완료 (배포 라이선스 정합성 1차 점검).** 코어+CLI 대상 점검·문서화 완료. (a) clean-room 자체 점검: 원본 C 소스(apetag/gain_analysis/id3tag/mp3gain.c)와 직접 대조 → 전 모듈 부합(차용은 알고리즘·계수 수치·비트 레이아웃·태그 포맷·옵션 체계 등 저작권 비대상뿐, 코드 독립). (b) 조치 3건: 도움말 산문 재작성(a7bf719 — `_wrap_explanation`/`_full_usage`가 원본 산문 verbatim이라 옵션·동작 유지하고 설명 문장만 독립 표현으로), analysis.py 계수 출처 정직 기재(a7bf719 — 실질 출처는 gain_analysis.c ABYule/ABButter 상수표), 주석 표현 정리(816fe81 — "원본 X 동등"류 → 결과 대응·독립 구현 취지). (c) git 분리 확인: `git ls-files`로 원본 C·VB·exe·fixture·음원 전부 추적 제외 확인. (d) 의존성 매트릭스: numpy·scipy(BSD, 고지만) / PySide6(LGPLv3, 동적링크·고지·재링크 보장) / ffmpeg(외부 호출은 전파 없음=기본안, 동봉 시 LGPL 빌드만 허용·GPL 빌드 금지). 산출물 `docs/LICENSE_REVIEW.md`(72719fb) — GPT 교차검증·전문가 최종 확인용 근거. **전문가 최종 확인은 실제 배포 직전 남겨둠, 로컬 개인 사용 단계에선 불필요(2.3).**

**다음 = 8단계 GUI (PySide6, clean-room 재현).** 1~7단계 완료. 원본 MP3GainGUI(VB6) 동작을 실제 소스(frmMain.frm·frmOptions.frm)로 대조 확인 완료: GUI 는 계산을 안 하고 mp3gain.exe 를 호출해 stdout 을 파싱하는 프런트엔드이며, 목표 음량은 CLI 인자로 넘기지 않고(`targetChange` 가 `dblGainAdjust = 목표−89` 를 화면 표시용으로만 계산) CLI 는 항상 89 기준 분석·`/g <steps>` 적용, 결과 표시·클립 3색 판정은 `DispJunk` 가 수행함을 확증(이전에 "GUI 가 목표 dB 를 −d 로 변환"이라던 추정은 정정됨).

- **아키텍처 결정(합의)**: 코어 직접 import(subprocess 아님). **8단계 첫 하위작업 = 순수 함수 API 계층 분리**(print↔반환값 분리 리팩터링, 원본 재현 불변). CLI·GUI·AVD 공유. 상세는 6단계 로드맵 8번.
- **MVP 범위(합의)**: 컬럼 파일명/Volume/Track Gain/clip(3색)/Curr Max Amp, 버튼 Add·Analysis·Gain·Clear·진행률. Album·Constant·Max No-clip·트레이·로그·언어·정렬은 후순위. 목표 음량 89dB 기준 표기 명시. auto-clip 끔 + 지정값 적용 + 클립은 표시만. 상세는 6단계 로드맵 8번.
- **AVD 연결(확정)**: 다운로드 후 별도 단계로 함수 계층 호출(사후 폴더 처리).
- **다음 세션 시작점**: (a) CLAUDE.md 반영 후, (b) 함수 API 계층 설계에 착수하려면 `apply_gain.py`(`_fill_track_info`/`_fill_album_info`)와 `gaindb/tag.py`(MP3GainTagInfo 구조)·필요시 `gaindb/analysis.py` 를 붙여 제공. `_run_analysis` 에서 print 를 걷어내고 결과 객체를 반환하는 것이 핵심 작업.

[진척 10 - 8단계 API 계층 완료] gaindb/api.py 의 analyze_file(비파괴·무출력, dict 반환) 신설. CLI --show / GUI / AVD 가 공유하는 표시용 함수. 원본 MP3GainGUI(DispJunk/Mp3Info.cls)의 Volume·Track Gain·3색 클립 로직을 재현하되 두 가지를 의도적으로 조정: (1) Track Gain 표시 제수를 원본 화면용 근사 1.505 대신 정밀값 5*log10(2)=1.50514997831991 로 통일(원본도 실제 계산 RadioMp3Gain/AlterDb 엔 정밀값 사용). (2) 스텝 반올림을 원본 GUI 의 banker's rounding 대신 적용 경로(apply_track_gain)와 동일한 db_to_steps(round-half-away-from-zero)로 통일 → "표시된 스텝·dB·클립 = 실제 적용 결과" 항상 일치(표시Only 정책 핵심). 0.5dB 경계의 극소수 곡에서 원본 GUI 표시와 1스텝(약 1.5dB) 다를 수 있으나 이는 우리 적용 결과와 정합하는 올바른 값. analysis.py 에 공개 별칭 DB_PER_STEP 노출. mp3gain_cli.py 는 원본 재현 _run_analysis 를 보존하고 --show 서브커맨드(_run_show)를 신설해 analyze_file 을 노출(원본 재현 자산 손상 없음). 검증: Debussy(89→96dB 시 steps 0→5, clip none→definite), 10cm(-6dB), 전 샘플레이트(8k~44k)·mono/stereo 정상. 다음 = GUI(PySide6) 레이어에서 analyze_file 직접 호출로 리스트뷰 구성.

[진척 11 - 8단계 GUI 골격·정렬·폰트·색상 완료] gui/ 패키지 신설(clean-room, VB6 코드 미차용, 화면 구성·동작 관찰만). 구성 4파일: columns.py(Col IntEnum NAME/VOLUME/TRACK_GAIN/CLIP/MAX_AMP, ColumnDef frozen dataclass[index·header·align·sort_key], COLUMNS 튜플, 헤더 "Path\File"/"Volume"/"Track Gain"/"clipping"/"Curr Max Amp"), model.py(FileRow dataclass[path·result·status·error_msg + set_result/mark_applied/mark_error/clear_result], SORT_ROLE=UserRole+1, FileTableModel[QAbstractTableModel]), main_window.py(collect_mp3_paths 순수함수·재귀, NaturalSortProxy[QSortFilterProxyModel], MainWindow), __main__.py(python -m gui 진입점). 구현·검증 완료 사항:

- NAME 컬럼은 basename 아닌 전체 경로 표시(원본 mp3gain Path\File 동일, 2.1). 초기 정렬 = NAME 오름차순 명시(sortByColumn AscendingOrder), 헤더 클릭 오름↔내림 토글 정상.
- 자연 정렬(합의됨, 원본 VB 문자열 정렬과 달리 Windows11 탐색기식): NaturalSortProxy 가 SORT_ROLE 로 typed 값 받아 QCollator(numericMode=True, CaseInsensitive)로 파일명의 숫자 부분을 실제 크기 비교, 수치 컬럼은 값 비교, 미분석(None)은 정렬 방향 무관 항상 뒤로. 삭제 시 proxy.mapToSource 로 원본 행 변환(정렬 상태 오삭제 방지).
- 다크테마 안전 색상(하드코딩 회피): clip 색은 possible=파랑·definite=빨강만 지정, none 은 미지정으로 OS 팔레트에 위임(원본 vbBlack 하드코딩 시 다크모드 파일명 안 보이던 문제 해결). ForegroundRole 로 clip 컬럼에만 적용.
- 플랫폼 폰트(하드코딩 회피, macOS 대비): __main__.py 에서 Windows 만 QFont("Segoe UI Variable Text") 지정하되 QFontInfo 로 실제 해석 확인 후 적용(구형 Win 폴백), macOS/Linux 는 시스템 기본(San Francisco 등) 그대로. 조사 근거: Win11 실기본은 Segoe UI Variable(Latin/Greek/Cyrillic 전용, 한글은 Malgun Gothic 폴백)인데 Qt 는 구형 Segoe UI 로 매핑 → 대문자 T 자간 좁아 "Tr"/"Tar" 붙던 현상. Variable Text 지정으로 optical size 축 작동해 해소 확인.
- 파일 추가: Add Files/Add Folder 버튼 + 창 전체 드래그앤드롭(원본 lstvMain_OLEDragDrop 대응), 폴더 재귀 기본 켜짐(원본 mnuAddSubs). 중복 제거는 모델 add_paths(_seen set). Clear = 선택 행만/없으면 전체.
- 유니코드 파일명 완전 지원 확인(원본 대비 개선): 한자 파일(official髭男dism - Pretender.mp3)이 목록·표시·ffmpeg 디코딩·analyze_file 까지 정상(status ok). 원본 VB6 는 ANSI/CP949 한계로 髭 등 미지원이었으나 우리는 Python3 유니코드 + ffmpeg subprocess 로 통과. 별도 인코딩 보강 불필요.
- Track Analysis / Track Gain 버튼은 아직 상태바 메시지만 띄우는 배선 상태(워커 미연결). Target Volume QDoubleSpinBox(75~105, 기본 DEFAULT_TARGET_DB=89), 진행바+Cancel(미연결)·상태바 배치 완료.
- 커밋: 1464907(columns/model), 8b2c082(정렬 프록시·전체 경로·다크색상·플랫폼폰트). PySide6 6.11.1.

**[진척 12 - 8단계 순서 3·4 완료: AnalyzeWorker 연결 + 추가 시 태그 스캔 + 리스트 UX]** (커밋 65c428f)

- **AnalyzeWorker(QThread) 연결** (`gui/workers.py` 신설). Track Analysis 가 `gaindb.api.analyze_file` 을 워커에서 호출. 시그널 progress(done,total)/row_done(path,result)/failed(path,msg)/done(). 취소는 파일 경계에서만(진행 중 ffmpeg 강제중단 안 함). 워커는 시그널만 방출, 모델 변경은 전부 메인 스레드 슬롯에서(row_done→set_result, failed→mark_error). 무거운 ffmpeg 디코딩이라 스레드 분리 필수. 분석 중 버튼 잠금(`_update_action_states` busy 분기).
- **Track Analysis 대상(합의됨)**: "선택 행 있으면 선택, 없으면 전체". 단 그중 **값이 아직 없는 행만** 분석(`FileRow.needs_analysis()`, status not in analyzed/applied). 원본 `Radio()` 의 `RadiodBGain=NOREALNUM` 체크 재현 — 이미 값 있는 파일은 건너뜀.
- **추가 시 태그 동기 스캔** (원본 `AddSingleFile` 의 `/o /s c` 대응). `gaindb/api.py` 에 `read_file_tags(path, target_db)` 신설 — 태그만 읽어(디코딩 없음, 곡당 ~1ms) 표시값 반환. status "ok"(태그에서 track_gain 읽음, 분석 불필요) / "no_tag"(track_gain 없음, 분석 필요). 태그 있는 파일은 추가 즉시 Volume/Track Gain/clip 표시, 없는 파일은 빈칸(원본과 동일). **동기 처리(합의됨)**: 태그 읽기가 가벼워 추가 흐름 안에서 메인 스레드가 직접 처리(원본도 동기; 원본은 더 무거운 subprocess 인데도 동기 + DoEvents). 대량 추가 시 버벅이면 후순위로 워커화.
  - 매핑 확정: 원본 `RadiodBGain`=우리 `MP3GainTagInfo.track_gain`(89dB 기준 raw dB, `_fill_track_info` 가 raw dB 그대로 저장), 원본 `CurrMaxAmp`=`track_peak*32768`, `CurrMin/MaxGain`=`min/max_gain`. `_compute_display` 에 peak=None 분기 추가(태그에 peak 없으면 clip "none", 원본 DispJunk 의 CurrMaxAmp=NOREALNUM 대응).
- **표시Only 재확인**: 분석·태그스캔은 파일 **불변**(read_file_tags=읽기만, analyze_file=계산만). 실제 기록은 Track Gain(순서 5, 미연결)뿐. 원본도 Track Analysis 는 표시만·Track Gain 이 기록. 현재 GUI 로는 어떤 경우에도 파일 변경 없음.
- **목표 변경 시 재표시**: `_on_target_changed` 가 값 있는 전 행에 `recompute_target` 적용 후 `row_changed`(재분석 없음). 원본 `targetChange`→`GainAdjust`→`DispJunk`. status 는 analyzed 유지 → 목표 바꿔도 재분석 대상 안 됨.
- **리스트 UX 원본 대조·보강**: (a) Delete 키 = 선택 행만 삭제(`FileTableView.keyPressEvent`, 원본 `lstvMain_KeyDown` KeyCode 46→ClearFiles; 선택 없으면 무동작=전체삭제 아님, Clear 버튼과 구분). (b) 더블클릭 재생(`_on_double_click`→`open_with_default_app`, 원본 `lstvMain_DblClick` 의 ShellExecute; 플랫폼 분기 win=os.startfile/mac=open/linux=xdg-open; 정렬 상태서도 mapToSource 로 정확한 곡). (c) 빈 영역 고무줄 선택(`FileTableView` mousePress/Move/Release + QRubberBand; QTableView 는 setSelectionRectVisible 이 없어=QListView/QTree 전용, 직접 구현; 행 위 시작은 super() 위임, Ctrl 시작은 기존 선택에 추가). Ctrl+A 전체선택은 QTableView 기본. `add_paths` 반환을 bool→추가 행 인덱스 리스트로 변경(추가 직후 태그 스캔 대상 지정용).

**8단계 순서 3·4 완료.** (미구현이던 순서 5 = 아래 진척 13 에서 완료.)

- **후순위(원본에 있으나 MVP 제외)**: 우클릭 팝업 메뉴(Album/Undo/RemoveTags/Play 등), 컬럼 순서·폭 저장/복원, 정렬 상태 저장, Album·Constant·Max No-clip, 트레이·로그·언어메뉴. **드래그 중 뷰 밖 자동 스크롤(고무줄 선택 확장)은 미구현 — 현재는 보이는 범위 내에서만.** 필요 시 후속 보강(당면 불편은 크지 않다고 판단, 사용자 확인).

**[진척 13 - 8단계 순서 5 완료: Track Gain 적용 + GUI UX 마감]** (커밋 551d2b8·c9c7650·28f04e1·b4f2bbe 등)

- **ApplyWorker(QThread) 연결** (`gui/workers.py`). Track Gain 버튼이 대상 행의 경로+기존 result 를 씨앗으로 넘겨 워커를 띄운다. 워커는 파일별로 원본 `RadioGain` 재현: (a) 미분석이면 `analyze_file` 로 먼저 분석 → (b) 스텝 0 이면 적용 없이 분석 결과만 방출(`row_analyzed`, 원본 "분석까지만") → (c) 스텝 있으면 `apply_file_track_gain`(파괴적) 후 `shift_after_apply` 로 표시 dict 방출(`row_applied`). 시그널 progress/row_analyzed/row_applied/failed/done. 모델 변경은 메인 스레드 슬롯에서만. 대상 규칙 "선택 있으면 선택·없으면 전체"(원본 mnuSelectedFiles), 값 있는 행도 포함(원본은 RadiodBGain 있으면 재분석만 생략). 원본 확증: `/g` 실행은 `RadioMp3Gain<>0` 일 때만, 적용 성공 시 `AlterDb -steps*FIVELOG10TWO` 로 메모리 dB 이동 후 DispJunk(재분석 없음).
- **표시 수식 3건 정정(Mp3Info.cls·DispJunk 대조, 커밋 551d2b8)**: (1) **Volume = 89 − raw**(원본 `DEFAULTTARGET + ModifydBGain − RadiodBGain` 에서 ModifydBGain 상쇄 → 목표 무관 "현재 실제 음량"; 기존 `target − raw` 오류). (2) **shift 부호**: 적용 후 raw 를 `−steps×DB_PER_STEP` 로 낮춤(원본 AlterDb `mvarRadiodBGain += -steps*FIVELOG10TWO`; 기존 `+` 로 Track Gain 이 0 으로 수렴 안 하던 버그 해결). (3) **peak 갱신**: shift 시 curr_max_amp `×2^(steps/4)`(원본 AlterDb; 누락으로 목표 왕복 시 거짓 clip 뜨던 버그 해결 — 9 함정 등재). clip possible 분기는 원본대로 target 기준 볼륨(`83 − (target − raw)`).
- **원본 exe 실측 검증**: 104 사본을 `mp3gain.exe -s s` 스캔 → Max PCM 17195.6·Track dB 0.51·gain 0. 우리 `--show` 완전 일치(CurrMaxAmp 17196·Volume 88.5·clip 없음). GUI 4파일도 원본 GUI 와 Volume·Track Gain(0.0)·CurrMaxAmp·clip 전부 일치(목표 97·89 양쪽, 스크린샷 대조).
- **툴바 단축키**(원본 frmMain.frm 메뉴 재현): Add Files=Ctrl+F, Add Folder=Ctrl+D, Track Analysis=Ctrl+T, Track Gain=Ctrl+G(원본 mnuAddFile/mnuAddFolder/mnuRadio/mnuRadioGain 동일). Clear 는 원본에 없어 편의로 Ctrl+Shift+Delete(전체 삭제=파괴적, 3키로 오발 방지, 합의). setShortcut + 툴팁 표기. busy 시 QAction 비활성화 → 단축키도 막힘.
- **Clear 동작 정리(원본 2분리 재현)**: **Clear 버튼/Ctrl+Shift+Delete = 항상 전체 삭제**(원본 ClearAll, 선택 무관, 확인창 없음=원본도 없음), **Delete 키 = 선택 삭제**(원본 ClearFiles/lstvMain_KeyDown KeyCode 46). 목록만 비우고 파일 미변경.
- **Track Analysis 태그 미기록 확증(원본 소스 대조)**: 원본 Radio→RadioSingleFile 은 `mp3gain /o ...` 로 stdout 출력만 받아 메모리·화면에만 반영, 파일·태그 미변경(/o=출력전용). 태그 기록은 Track Gain(/g)의 changeGainAndTag 경로뿐. 우리 analyze_file(비파괴·무출력)·apply_file_track_gain(태그 기록)과 정합 → **Track Analysis 에 태그 기록 추가 안 함이 원본 동일 재현**(사용자 확인).

**8단계 MVP 사실상 완성(핵심 흐름).** 완료: 파일/폴더 추가·태그 스캔·자연 정렬·다크색상·유니코드·리스트 UX(Delete/더블클릭/고무줄)·Track Analysis(AnalyzeWorker)·Track Gain(ApplyWorker, 원본 RadioGain 재현)·표시 수식(원본 exe 실측 일치)·단축키·Clear 정리.

- **미검증(다음 점검 권장)**: 진행바·Cancel 실동작 최종 확인(배선은 됨), 대량 추가 시 태그 스캔 버벅임 여부, 오염된 목록은 Clear 후 재추가로 태그 재스캔.
- **다음 세션 시작점**: CLAUDE.md 첨부 후 택일. (a) **잔여 MVP 최종 점검** → `gui/main_window.py`·`gui/workers.py`. (b) **GUI 순수 함수부 tests 편입 검토**(collect_mp3_paths·표시 수식·shift/recompute; 파괴적 적용은 fixture 사본으로만, 원본 불간섭 9) → `gaindb/api.py`·`gaindb/analysis.py`·`tests/_support.py`. (c) **후순위 기능 착수**(우클릭 팝업=Album/Undo/RemoveTags/Play, 컬럼폭·정렬 저장, Album/Constant/Max No-clip, 트레이·로그·언어) → 해당 원본 폼(frmMain 팝업·frmOptions·frmGetGain 등) 붙여 제공. 우선순위는 사용자 결정.
