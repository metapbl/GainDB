# Gain dB — Claude 컨텍스트 파일

> 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하는 컨텍스트 파일.
> 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고, 그 세션 단계에 필요한 원본 소스를 함께 붙여넣는다(자세한 방법은 "5. 원본 참고 자료 · 새 세션 시작법" 참조).

---

## 1. 프로젝트 정체성

- **표시 이름**: Gain dB / **기술 이름(폴더·저장소·패키지)**: `GaindB`
- **성격**: MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구. 원본 MP3Gain 의 기능·동작·태그 포맷·출력과 **호환되도록 결과를 일치**시키되, 원본 C 코드를 옮기는 "포팅"이 아니라 공개 사양·관찰된 동작만 보고 **독립 구현**한다(원칙 상세는 2 참조).
- **범위**: **MP3 단독 전용**. AAC/FLAC/Opus 등 타 포맷은 다루지 않는다(원본 mp3gain 본체도 MP3 전용, 무손실 게인 기법이 MP3 고유 구조라 타 포맷에 원리적으로 적용 불가 — 3 참조).
- **위치**: AVD(AV_Downloader)로 "MP3 지정" 다운로드한 음원의 음량을 고르게 맞추는 **후속 단계 도구**. 단독으로도 동작.
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\GaindB`
- **협업 모델**: 1인 개발자 + AI 페어 프로그래밍. 버전관리는 로컬 Git. GitHub 오픈소스 공개(Apache 2.0) 예정.
- **장기 비전**: GaindB(코어+CLI) 완성 후 PySide6 GUI 를 얹어 Windows·macOS 크로스플랫폼 프로그램으로 만든다(8단계). 나아가 기존 AVD 프로젝트(https://github.com/metapbl/AVD)와 병합해 다기능 유틸리티로 발전시키는 것이 큰 그림이다(병합은 그 이후의 비전이며, 당면 목표는 GaindB 자체의 완성과 GUI MVP).

## 2. 핵심 원칙 (최우선 · 어떤 압축·개정에서도 약화 금지)

프로젝트 전체를 관통하는 세 원칙이며 서로 한 몸이다: mp3gain 호환성, 독립 구현, 그 위의 라이선스 정책. 완료분의 how 는 압축해도, 이 원칙과 합의·미완·제약의 what 은 보존한다.

### 2.1. mp3gain 호환성 (결과 일치)

- 원본 mp3gain 의 **기능·동작·태그 포맷·출력·옵션과 상호운용 가능하도록**, 결과(동작·태그 포맷·출력·수치)를 일치시킨다. 임의로 기능을 빼거나 단순화하지 않는다.
- "호환"은 **결과의 일치**를 뜻하며 코드의 일치가 아니다. 구현은 원본 코드를 옮기지 않고 공개 사양·관찰된 동작으로 독립 작성한다 — 결과는 일치, 코드는 독립.
- 불가피하게 일부를 미루거나 예외를 두어야 할 때 **Claude 가 임의로 정하지 않는다.** 반드시 사용자와 합의하고, 그 결정을 10 진척 로그에 "축소가 아니라 합의된 예외 / 진행 중 미완"임이 드러나게 명시한다.
- 이미 합의된 예외/우선 구현(기능 축소가 아님):
  - **디코더(항구적 예외)**: PCM 추출은 원본의 `mpglibDBL` 디코더 대신 외부 도구(ffmpeg)를 호출한다. 실용성 때문이며, 구현 수단만 다를 뿐 분석 결과(라우드니스 dB)는 mp3gain 과 일치시킨다(2.3 참조).
  - **샘플레이트(확장 완료)**: 실제 음원 다수인 44.1k·48k 를 먼저 구현·검증한 뒤, ReplayGain 사양의 나머지 샘플레이트(32k 및 MPEG2/2.5 계열)까지 확장·검증 완료. 계수는 공개 표준값 전사(재설계 불가 사유·판단은 10.2).

### 2.2. 독립 구현 원칙

이 프로젝트의 **모든 구성 요소**는 독립 구현한다 — 코어(`gaindb/`)·CLI 는 물론, GUI(8단계)와 그 이후 어떤 확장이든 예외 없이 적용된다. 원본 MP3Gain 의 어떤 코드(C 본체든 VB GUI 든)도 직접 번역·복붙하지 않는다. 다른 언어로 옮기는 것도 2차적 저작물이므로 금지한다. 우리가 차용하는 것은 **저작권 대상이 아닌 것** — 알고리즘, 파일·태그 포맷, 비트 레이아웃, 필터 계수 수치, 옵션 체계, 화면 구성·동작 같은 공개 사양과 관찰된 동작뿐이다. 그 위에서 결과(동작·포맷·출력·외관)는 mp3gain 과 일치시키되 코드는 독립 작성한다.

> 용어 주의: 이 프로젝트는 엄격한 의미의 "clean-room"(원본을 본 적 없는 격리된 팀이 사양서만 받아 구현하는 절차)이 **아니다**. 개발 과정에서 원본 소스를 사양·동작 이해 목적의 참고 자료로 열람했다. 따라서 문서·주석·출력 어디에도 "clean-room"이라는 표현은 쓰지 않는다. 정확한 성격은 **"공개 사양과 관찰된 동작에 기반한 독립 재구현"**이며, 방어 논거는 clean-room 절차가 아니라 "차용 대상이 모두 저작권 비대상(아이디어·사실·수치·인터페이스)이라는 점"에 있다(2.3).

원본 소스(C·GUI 모두)는 참고 자료로만 로컬 보관하며 git 및 배포물에서 제외한다.

### 2.3. 라이선스 정책 (완전 독립 노선 · Apache 2.0 공개)

- 원본 MP3Gain 은 C 로 작성된 **LGPL v2.1** 오픈소스(2009년경 개발 중단). Windows GUI(MP3GainGUI)도 LGPL.
- 이 프로젝트는 원본 소스 코드를 **한 줄도 포함하지 않는다.** 차용한 것은 저작권 대상이 아닌 요소(알고리즘·파일/태그 포맷·비트 레이아웃·표준 계수 수치·옵션 체계·관찰된 UI 동작)뿐이므로, 결과물에 원본의 LGPL 이 파생·적용되지 않는다. 이는 "라이선스 회피"가 아니라 **애초에 저작물 복제가 없어 라이선스 대상이 아니라는** 사실 판단이다.
- **완전 독립 노선**: 원본 저작자(Glen Sawyer 등)에 대한 저작권 표기를 코드·CLI 출력·GUI 어디에도 넣지 않는다(포함한 원본 코드가 없으므로 표기 의무가 없고, 표기 시 파생물이라는 오해를 부른다). 원본에 대한 사실 언급은 NOTICE/README 에서 "mp3gain 의 알고리즘·포맷과 호환되는 독립 구현이며 원본 소스를 포함하지 않는다"는 취지의 서술로만 다룬다.
- **코드 자체는 Apache License 2.0 으로 GitHub 에 공개한다.** 특허 방어 조항이 있고 오디오/코덱 인접 영역·향후 확장(AVD 병합)에 유리하다. 저작권 표기 이름은 프로젝트 소유자로 하며 원본 저작자는 넣지 않는다. 필터 계수의 1차 출처(ReplayGain 공개 사양)는 정직하게 병기한다.
- **외부 의존성**: ffmpeg 는 PATH 의 외부 프로세스로 호출하며 동봉하지 않는다(사용자 설치, README 안내). PySide6 는 LGPLv3 로 동적 링크·사용자 재링크 보장·고지·라이선스 텍스트 동봉으로 준수한다. 릴리스 바이너리를 만들 경우에만 후자의 의무가 실제 발생하며, 소스 공개(사용자가 pip 설치) 형태에선 부담이 거의 없다.
- 실제 공개 배포 직전의 최종 확인은 자격 있는 전문가(변호사) 검토를 남겨둔다. **AI 는 성능·교차 여부와 무관하게 법적 책임·자격을 대체하지 못한다.** AI 교차검토는 쟁점 정리용 1차 참고에 그친다.

## 3. 핵심 기술 원리

- **무손실 음량 조정**: MP3 각 프레임의 사이드 정보 안 `global_gain`(8bit) 필드를 직접 ±N 하여 음량 조절. 디코더는 `2^(gain/4)` 로 샘플을 곱하므로 1스텝 ≈ 1.5dB. 재인코딩 없음 → 무손실. **MP3 고유 구조라 타 포맷에 적용 불가**(범위를 MP3 전용으로 못박는 근거).
- **음량 분석**: PCM 으로 디코딩 후 David Robinson 의 ReplayGain 알고리즘(equal-loudness 필터 + RMS + 통계, 95퍼센타일 부근)으로 인지 음량 계산. 목표값(기본 89dB)에 맞추는 데 필요한 게인 스텝 수를 산출.
- **Track gain / Album gain** 두 모드. Album 은 곡별 히스토그램을 누적해 단일 dB 산출 후 전 곡에 동일 스텝 적용.
- **태그(원본 전 기능 재현 대상)**: 원본은 APEv2(기본) 또는 ID3v2(`-s i`) 태그에 다음을 기록·읽기·갱신·제거한다 — ReplayGain 표준 필드(`REPLAYGAIN_TRACK_GAIN`/`_PEAK`, `REPLAYGAIN_ALBUM_GAIN`/`_PEAK`, ID3 는 추가로 RVA2 프레임·`replaygain_reference_loudness`), mp3gain 고유 필드(`MP3GAIN_MINMAX`, `MP3GAIN_ALBUM_MINMAX`, `MP3GAIN_UNDO`). 게인 적용 시 이 값들을 일관되게 갱신한다(undo 누적, gain 에서 dB 차감, peak 에 2^(N/4) 곱, minmax 에 N 가감). undo 는 이 누적된 역방향 값으로 원복한다.

## 4. 기술 스택 · 저장소 구조

- **언어**: Python 3 (3.13/3.14 등). 프레임 파서·writer 는 순수 표준 라이브러리(외부 의존성 없음).
- **신호처리**: numpy + scipy (필터·RMS·통계).
- **MP3 디코딩(PCM 추출)**: 외부 도구(ffmpeg 직접 호출) — 원본 `mpglibDBL` 디코더는 옮기지 않는다(2.1 합의된 항구적 예외). ffmpeg 는 PATH 호출(동봉 안 함, 사용자 설치).
- **GUI**: PySide6 (Qt for Python, LGPLv3). Windows·macOS 크로스플랫폼. AVD 프로젝트와 스택 일치(향후 병합 대비). 기존 `gaindb/` 코어 + CLI 위에 얹는 프런트엔드(코어 재작성 없음).
- **가상환경**: venv (`.venv`).

루트: `C:\Users\ggoyo_zhxlvdr\GaindB` (구조가 바뀌면 이 트리와 10 진척 로그를 함께 갱신한다.)

GaindB/
├─ gaindb/                 # 코어 패키지 (순수 로직 + 분석)
│  ├─ __init__.py
│  ├─ frame.py             # 프레임 파서: _BitReader, 헤더 파싱, global_gain 읽기
│  ├─ writer.py            # global_gain ±N 무손실 적용 + CRC 재계산
│  ├─ decode.py            # ffmpeg/ffprobe 로 MP3→PCM (스트리밍 포함)
│  ├─ id3.py               # ID3v2 태그(RVA2 + TXXX) 읽기/쓰기
│  ├─ tag.py               # APEv2 태그(전 필드 + undo)
│  ├─ analysis.py          # ReplayGain 분석(Track/Album), dB→스텝 변환
│  ├─ api.py               # 비파괴 analyze_file (CLI/GUI/AVD 공유 진입점)
│  └─ apply_gain.py        # 게인 적용 로직(수동/auto/album)
├─ gaindb_cli.py           # 통합 CLI 진입점(mp3gain 호환 옵션 체계)
├─ gui/                    # PySide6 프런트엔드(8단계, 독립 구현)
│  ├─ __init__.py
│  ├─ __main__.py          # 진입점: QApplication, i18n 배선
│  ├─ main_window.py       # 메인 창: 리스트·분석/게인·우클릭·취소·트레이 배선
│  ├─ model.py             # Qt 테이블 모델(FileTableModel)
│  ├─ columns.py           # 컬럼 정의(QT_TRANSLATE_NOOP 헤더)
│  ├─ workers.py           # QThread 워커(분석/게인/앨범, 진행·취소)
│  ├─ logging.py           # 로그 파일 기록(Qt 비의존)
│  ├─ i18n.py              # 다국어 인프라(런타임 전환·로케일 폴백)
│  ├─ resources.py         # 아이콘 등 리소스 헬퍼
│  ├─ dialogs/
│  │  ├─ __init__.py
│  │  └─ logs_dialog.py    # 로그 보기 다이얼로그
│  └─ translations/        # 다국어 리소스
│     ├─ .gitkeep
│     ├─ gaindb_ko.ts      # 한국어 번역 소스
│     └─ gaindb_ko.qm      # 한국어 번역 컴파일본
├─ assets/
│  └─ GainDB.png           # 트레이·앱 아이콘
├─ tests/                  # 통합 테스트 스위트(unittest, 외부 의존 없음, 139건 PASS)
│  ├─ __init__.py
│  ├─ _support.py                   # 공용 헬퍼(FixtureGuard, audio_body_sha256 등)
│  ├─ _gen_fixtures.py              # 합성 fixture 생성기(저작권 음원 없음, git 공개)
│  ├─ test_support_smoke.py         # 테스트 헬퍼 자체 검증
│  ├─ test_roundtrip_options.py     # 무손실 round-trip + 옵션 조합
│  ├─ test_analysis_integration.py  # ReplayGain 분석 수치
│  ├─ test_tag_integration.py       # APE/ID3 태그 read/write/remove
│  ├─ test_useid3_migration.py      # -s i ID3 태그 경로
│  ├─ test_options_parsing.py       # CLI 옵션 파서
│  ├─ test_recalc_decode_skip.py    # recalc 비트마스크 디코딩 스킵
│  ├─ test_clip_integration.py      # 클리핑 판정·자동 클립(-k)
│  ├─ test_clamp_reversibility.py   # 255/0 클램프 비가역성(값 단위, fixture 무관)
│  ├─ test_samplerate_expansion.py  # 전 샘플레이트 계수
│  ├─ test_album.py                 # 앨범 게인 누적·peak 이동
│  ├─ test_logging.py               # 로그 파일 기록
│  ├─ test_cli_misc.py              # CLI 기타 분기(usage/version 등)
│  ├─ test_gui_pure.py              # GUI 순수 함수부
│  └─ test_streaming_analysis.py    # 스트리밍=통짜 비트 동일성
├─ docs/                    # (공개) 필요 시 사용자용 문서. 
├─ LICENSE                 # Apache License 2.0 전문
├─ NOTICE                  # 독립 구현·의존성 사실 고지
├─ CLAUDE.md               # 이 컨텍스트 파일
├─ .gitignore
├─ .vscode/                # 에디터 설정(git 제외)
└─ _local/                 # 원본 참고 소스·저작권 음원·수동 검증(git·배포물 제외)
   ├─ mp3gain/             #   원본 C·VB GUI 소스(사양·동작 참고용, 저장소·배포물에 미포함)
   ├─ manual_checks/       #   mutagen/exe 상호운용·대조 스크립트
   ├─ LICENSE_REVIEW.md    #   (비공개) 라이선스 정합성 점검 + 파일별 저작권 감사 통합 문서
   └─ test_audio/          #   합성 fixture(_gen_fixtures.py 가 생성, git·배포물 제외)

git 이 추적하는 것(= GitHub 공개 대상)은 위 트리에서 `_local/`·`.vscode/`·`__pycache__/`·`.venv/` 를 제외한 47개 파일이다(2026-07-24 스캔, `git ls-files` 실측).
원본 참고 소스와 저작권 음원은 전부 `_local/` 아래로 격리되어 저장소·배포물에 포함되지 않는다. 원본 exe 는 코드가 아니라 실행 결과만 검증 기준으로 쓰므로 독립 구현 원칙 위반이 아니다(2.2 의 "관찰된 동작 차용").

## 5. 원본 참고 자료 · 새 세션 시작법

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `_local/mp3gain/src/` 에 보관**. git·배포물 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- **원본 Windows GUI(MP3GainGUI)는 VB 로 작성된, CLI `mp3gain.exe` 를 호출하는 프런트엔드**다. 소스를 로컬에 보관(git·배포물 제외). 8단계에서 화면 구성·동작을 관찰·참고하되 코드는 옮기지 않는다(2.2).
- **이 미러의 `.c` 는 크롤 불가**(`application/octet-stream` MIME). 그래서 C·VB 소스는 로컬 보관 + 사용자가 붙여넣어 제공. Claude 가 크롤로 가져오려 시도하지 말 것.
- **새 세션 시작**: 첫 메시지에 본 파일(CLAUDE.md)과 `_local/LICENSE_REVIEW.md`(비공개 라이선스 감사 통합 문서)를 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다. 이어 그 세션 단계에 필요한 소스(.c/.h 또는 GUI, 또는 감사 대상 .py)를 붙여넣어 제공한다. 검색 도구는 최신 정보 확인용으로만 쓰고, 원본 소스 입수에는 쓰지 않는다.

## 6. 구현 단계 로드맵

> 작업을 나누기 위한 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다**(2.1). 각 단계의 완료 세부·확정된 결정은 10 참조.

1. **[완료] MP3 프레임 파서 + `global_gain` 읽기/쓰기** — 순수 Python. 읽기·쓰기·무손실 round-trip 검증.
2. **[완료] ReplayGain 분석기** (numpy/scipy) — equal-loudness 필터 + RMS + 통계, Track/Album gain, dB→스텝 변환.
3. **[완료] MP3 디코딩(PCM 추출)** — ffmpeg/ffprobe subprocess.
4. **[완료] 태그 처리** — APEv2·ID3v2 읽기·쓰기·갱신·제거, scan_gain, change_gain_and_tag, undo, auto/album 연결.
5. **[완료] CLI / 옵션 / 일괄 처리** — mp3gain 옵션 전부 재현, 클리핑 경고·자동 클립(`-k`), database 출력(`-o`) 포함. 통합 테스트 스위트로 검증.
6. **[완료] 샘플레이트 확장(호환 완결)** — ReplayGain 사양 전 샘플레이트를 코어에 추가·검증.
7. **[완료] 배포 라이선스 정합성 준비·검토** — 독립 구현 자체 점검 + LGPL 비적용 근거 정리 + Apache 2.0 노선 확정 + 파일별 저작권 위험 전수 감사(8.8). 최종 확인은 배포 직전 전문가(변호사) 검토로 남겨둔다(2.3).
8. **[MVP 완료·잔여 점검 중] GUI (PySide6, 독립 구현)** — 원본 MP3GainGUI 의 외관·기능·동작을 PySide6 로 결과 일치시키되 VB 코드를 옮기지 않고 공개 동작만 보고 독립 구현(2). 기존 코어 + CLI 위에 얹는 프런트엔드. Windows·macOS 크로스플랫폼. 확정된 아키텍처·MVP 범위·표시 정책·AVD 연결·잔여 항목은 **10.2·10.3 참조**.

## 7. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell 7.6.3). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만. (GUI 는 macOS 동작도 목표.)
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits(`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: `>` 리다이렉션은 UTF-16 LE BOM 으로 쓴다. 파일 쓰기는 BOM 없는 UTF-8 을 명시한다(`Out-File -Encoding utf8NoBOM`, 또는 한글 포함 시 `.NET` `UTF8Encoding($false)` + `WriteAllText`).
- **이 파일 관리**: 컨텍스트 파일은 짧게 유지한다. 단계 완료 시 10 진척 로그만 갱신하고, 끝난 단계의 세부 구현 설명은 한두 줄로 압축한다. **단, 2 핵심 원칙을 약화시키는 방향으로는 압축·수정하지 않는다** — 완료된 것의 how 는 압축, 합의·미완·제약의 what 은 보존.

## 8. Claude 응답 규칙 (진행 순서대로)

실제 협업 흐름은 조사·진단 → 원칙 합의 → 설계 → 코드 확인 → 코드 제시 → 디스크 반영·커밋 순이다. 아래 규칙도 그 순서를 따른다.

### 8.1. 범위·원칙 고수

- **범위**: MP3 전용이다. 타 포맷 지원 제안은 하지 않는다(무손실 게인은 MP3 `global_gain` 기법이라 원리적으로 타 포맷 적용 불가; 원본 mp3gain 본체도 MP3 전용).
- **mp3gain 호환 + 독립 구현**: 원본 기능을 임의로 빼거나 단순화하지 않는다(2.1). 무언가를 미루거나 예외로 두려면 먼저 사용자와 합의하고 10 에 명시한다. 사용자가 제공한 원본 C·VB 소스는 사양·동작 이해 목적으로만 읽고 코드를 그대로 옮기지 않는다(2.2). 알고리즘·비트 레이아웃·필터 계수·태그 포맷·UI 동작 같은 공개 사양만 차용해 독립 재작성한다.

### 8.2. 설계·진단이 먼저

코드보다 설계·진단·합의가 앞선다. 코드 블록을 보내기 전 "코드를 보내드릴까요?" 라고 한 박자 묻고, 동의 후 다음 응답에서 제시한다.

### 8.3. 코드 제시 단위

- 변경이 **함수 2개 이하**에서만 일어나고 모듈 최상위를 안 건드리면 → 변경된 함수를 개별 코드 블록으로 **함수 단위 발췌**.
- 그 외(함수 3개 이상·최상위 변경·새 함수·시그니처 변경) → **파일 전체**.
- 어느 경우든 코드 블록 바깥에 변경 지점을 한 문장으로 명시.

### 8.4. 파일 반영은 반드시 코드블록 또는 터미널 명령으로

파일(`.py`·`.md`·`.gitignore` 등)에 반영할 내용은 맨몸 텍스트로 흘려보내지 않고 둘 중 하나로 감싼다.

- **파일 전체 신규·교체** → here-string 터미널 명령: 코드 전체를 리터럴 here-string 으로 감싸 BOM 없는 UTF-8 로 저장. 사용자가 파일을 직접 열지 않고 VS Code 터미널에 붙여넣어 엔터만 치면 저장되게 한다. (리터럴 here-string 이라 백틱·달러·따옴표 안전. 단, 본문에 줄 맨 앞이 종료 구분자인 줄이 없어야 함 — 제시 전 확인.)
- **국소 수정·삽입/교체 조각** → 코드 펜스로 감싼 발췌. Claude 가 파일 전체 최신본을 정확히 보유하지 못하면 통짜 교체가 다른 부분을 훼손할 수 있으므로, 국소 수정은 통짜 교체보다 조각 발췌를 우선한다.

### 8.5. 터미널 명령 동봉

파일을 수정·추가·삭제하는 코드를 제시할 때는 디스크 반영·커밋 명령을 같은 응답에 함께 제시. 기본 흐름 (1) `git add <파일>` (2) `git status` (3) `git commit -m "..."`. 환경은 PowerShell, cwd=루트.

### 8.6. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 있으면 바깥 펜스는 안쪽보다 백틱을 하나 더 쓴다(안쪽 3개 → 바깥 4개, 그 안에 또 있으면 5개).

### 8.7. 서식

- 불릿은 대시 + 공백 1칸, 하위 불릿은 부모 기준 2칸 들여쓰기.
- 헤더 번호(깊이 2까지)는 **다른 곳에서 참조되는 섹션(2·8·10)에만** 붙인다. 나머지 최상위 섹션은 번호 없이 산문·불릿으로 둔다.
- 과한 볼드·리스트 남용 지양, 산문 우선.

### 8.8. 저작권 위험 전수 감사 절차 (완전 독립 노선)

파일별 세션에서 소스 트리를 하나씩 검토해 저작권 위험을 소거한다. 매 파일 동일 절차:
- **식별**: (A) 원본 저작권 표기, (B) "clean-room" 방어 프레임, (C) 원본 파일명·함수명·코드 참조 뉘앙스를 찾는다.
- **판정 기준**: 차용 가능(알고리즘·파일/태그 포맷·비트 레이아웃·표준 계수 수치·옵션 체계·관찰된 UI 동작·원본 exe 가 출력하는 문자열 = 저작권 비대상) vs 차용 불가(원본 소스 코드·설명 산문·독창적 표현).
- **유지 주의**: 일반 영어 변수명(`original_*`), 원본 exe 의 동작 결과 출력 문자열, 테스트가 검증하는 문자열은 건드리지 않는다.
- **처리**: (A) 삭제 → 사실 언급은 README/NOTICE 로만(2.3). (B) "독립 구현"으로 치환. (C) "mp3gain 과 동일한 결과" 등 결과 일치 서술로 중립화, 원본 파일명 직접 언급 최소화.
- **기록**: `_local/LICENSE_REVIEW.md`(비공개) 2부(파일별 감사)에 검토일·위험 유형·처리·유지 근거·커밋·상태를 남긴다.
- **검증**: 수정 후 `python -m unittest discover -s tests` 통과 확인 뒤 커밋.

## 9. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 프레임 파서의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함(1·6단계에서 해결·검증 완료).
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain·255-gain 프레임은 클램프로 비가역**: `gain==0` 이면 ±N 으로 안 바뀌고(하한 유지), `gain==255` 에 +N 하면 255 로 클램프되어 초과분이 소실된다(상한). round-trip 완전복원은 경계 프레임이 없거나 경계를 벗어나지 않는 방향으로 적용할 때만 보장된다(`_apply_one` 동작). 통합 테스트의 round-trip 은 상한/하한 클램프 회피를 위해 음수 스텝 먼저(-3) 후 복원(+3 또는 undo)으로 한다. 합성 fixture(`_gen_fixtures.py`)는 44.1k 계열 max global_gain=210(min≥8)으로 `_ROUNDTRIP_SAFE` 여유를 보장하므로 음수 방향이 안전하다. 255 클램프 자체의 비가역성은 fixture 로는 안 타므로 값 단위 테스트(`test_clamp_reversibility`)가 직접 검증한다.
- **mono 분석 경로 주의(3dB 버그 교훈)**: ffmpeg `-ac 2` up-mix 는 mono 를 각 채널 1/√2 감쇠시켜 라우드니스가 정확히 3dB(≈10·log10 2) 낮게 나온다. mono 는 ffprobe 로 채널 수를 조회해 `-ac 1` 로 원진폭 디코딩 후 코드에서 좌우 복제해야 한다. stereo 위주 검증의 사각지대였음.
- **표시 수식 3건(원본 실측 대조로 확정)**: (1) **Volume = 89 − raw**(현재 실제 음량, 목표 무관). (2) **적용 후 shift 부호는 하향**: raw 를 `−steps×DB_PER_STEP` 로 낮춘다(`+` 로 하면 Track Gain 이 0 으로 수렴 안 함). (3) **적용 후 peak(curr_max_amp)도 함께 이동**: `×2^(steps/4)` 갱신 후 clip 재판정. 누락하면 목표 왕복 시 거짓 clip 이 뜬다. 목표만 바꾸는 `recompute_target` 은 파일 미변경이므로 peak 를 건드리지 않는다.
- **타 포맷 적용 불가**(8.1) / **원본 코드 직접 번역 금지**(2.2) / **원본 기능 임의 축소 금지**(2.1).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 소스는 로컬 보관 + 사용자가 붙여넣어 제공(5). Claude 가 크롤로 가져오려 시도하지 말 것.
- **테스트는 원본 음원을 절대 건드리지 않는다(영구 제약, 오염 사고 재발함)**: 모든 검증·테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다. 각 테스트는 깨끗한 fixture(또는 `-s d` 로 태그 제거한 상태)에서 시작한다. 원본 두 음원에 mp3gain 태그가 남아 테스트가 실패로 보인 사고(코드 결함 아님, 원본 오염 탓)가 재발했다. **원본 경로를 검증 명령에 직접 쓰지 말 것.**
- **undo 0 태그는 남는다**: 깨끗한 파일에 `-g N` 적용 후 `-u` 하면 오디오 본문은 비트 동일로 복원되지만 `MP3GAIN_UNDO 0,0` APE 태그가 남아 파일 전체 해시는 달라진다. 무손실 검증은 전체 해시가 아니라 tag_offset 까지의 오디오 본문 해시(`audio_body_sha256`)로 판정한다.
- **numpy 배열의 truthiness 평가 금지(앨범 워커 전멸 교훈)**: `arr or []`·`if arr:` 처럼 numpy 배열을 boolean 문맥에 두면 "ambiguous" 예외가 난다. 히스토그램 등 배열은 반드시 `x if x is not None else []` 로 판정한다(길이 판단은 `len(x)`, 존재 판단은 `is not None`).
- **초장시간 곡은 통짜 디코딩 금지(메모리 폭증·UI 얼음 교훈)**: 곡 전체 PCM 을 메모리에 올리면 시스템이 스와핑으로 얼어붙고, 파일 경계에서만 취소하면 그 곡이 끝날 때까지 취소가 안 먹힌다. → 분석은 스트리밍(청크 흘림, 10.2), 취소는 청크 경계에서 ffmpeg 즉시 kill.
- **Track Gain 이중 디코딩 금지**: `apply_track_gain` 은 원래 씨앗 없이 매번 decode+analyze+scan 을 다시 했다. → 씨앗(seed_db_gain·seed_peak·seed_min_gain·seed_max_gain)을 선택 주입해 유효하면 decode/analyze/scan 을 건너뛴다(결과 수치 동일). 씨앗 peak 가 None 이면 자동으로 디코딩 경로로 폴백(안전).
- **적용 단계도 취소·진행 확인 지점을 가져야 함(취소 갇힘 교훈)**: `scan_gain`·`apply_gain` 은 순수 파이썬 프레임 순회라 디코딩이 없다. 두 함수에 should_cancel/on_progress 를 `_CALLBACK_INTERVAL`(=4096) 프레임마다 확인, 취소 시 `writer.GainCancelled`. 취소 확인은 파일 write 이전 순회 단계에서만 하므로 취소해도 파일은 원본 그대로.
- **255 클램프(비가역)와 클리핑은 별개**: 클램프는 global_gain(8bit)이 255 넘어 잘려 undo 왕복이 깨지는 데이터 손실, 클리핑은 PCM 진폭이 ±32768 넘어 소리가 왜곡되는 청취 품질 문제. 임계값·발생 지점이 달라 한쪽만 생길 수 있다. 원본 mp3gain 은 클램프를 경고 없이 조용히 255 로 자르고 진행(우리 `_apply_one` 동일) — 결과 일치라 별도 경고 안 함(사전 경고는 원본에 없는 추가 기능이라 MVP 제외).

## 10. 진척 로그 / 정책 / 다음 시작점

### 10.1. 완료 요약 (1~8단계)

**1~7단계 완료·검증 완료. 8단계 GUI MVP + 후순위 기능(우클릭 팝업·앨범 계열·컬럼저장·로그·트레이·다국어)까지 완료.** 세부 구현은 코드·git log 에 있으므로 여기선 "무엇을 완료했는가"만 남긴다.

1. 프레임 파서 + `global_gain` 읽기/쓰기(`frame.py`·`writer.py`, round-trip 바이트 동일).
2. ReplayGain 분석기(`analysis.py` — equal-loudness 필터+RMS+히스토그램+95퍼센타일−PINK_REF). Track 은 ffmpeg replaygain 과 허용오차 이내, Album 은 혼합 검증.
3. MP3 디코딩(`decode.py` — ffmpeg/ffprobe subprocess).
4. 태그(`tag.py` APE·`id3.py` ID3v2 — read/write/remove/round-trip, scan_gain, change_gain_and_tag, auto/album, 꼬리 보존, useId3 분기).
5. CLI(`gaindb_cli.py`) — mp3gain 옵션 전부 재현(게인·분석·적용·클립·database·태그). recalc 비트마스크로 디코딩 스킵(수치 일치). CLI I/O 는 영문만(다국어는 GUI 책임).
6. 샘플레이트 확장 — ReplayGain 전 샘플레이트(32k / MPEG2·2.5 계열) 코어 추가, exe 대조 min/max 전부 일치.
7. 배포 라이선스 검토 — 전 모듈 독립 구현 부합 확인, 계수 출처 정직 기재, git·배포물 분리, 의존성 매트릭스, Apache 2.0 노선 확정, 파일별 저작권 위험 전수 감사(8.8, `_local/LICENSE_REVIEW.md` 부록 A). 최종 확인은 배포 직전 전문가 검토로 남겨둠(2.3).
8. GUI(PySide6, `gui/`) — 파일/폴더 추가·태그 스캔·자연 정렬·유니코드·리스트 UX·Track/Album 분석·게인·우클릭 팝업(Clear Analysis/Undo/Remove Tags/Play)·취소(청크 경계 즉시 kill)·스트리밍 분석(수 시간 곡)·컬럼폭/정렬 저장·로그·트레이·다국어. 표시값은 원본 exe 실측과 일치. `api.analyze_file`(비파괴)이 CLI/GUI/AVD 공유.

**검증 인프라.** 통합 테스트 스위트(`tests/`, unittest, 외부 의존 없음) — `python -m unittest discover -s tests` 전부 PASS(139건, skip=0). fixture 는 저작권 음원이 아니라 `tests/_gen_fixtures.py`(합성 생성기, git 공개)가 고정 시드 신호에서 생성하며 산출물은 `_local/test_audio/`(git 제외); ffmpeg 필요. 모든 테스트는 fixture 불간섭(tempfile 사본, `FixtureGuard` 오염 감시), 무손실은 `audio_body_sha256`(오디오 본문만 해시)로 판정. 255/0 클램프 비가역성은 fixture 무관 값 단위 테스트(`test_clamp_reversibility`)로 별도 커버. 도메인별 모듈(roundtrip/analysis/tag/options/recalc/clip/clamp/useid3/samplerate/album/logging + GUI 순수 함수부 `test_gui_pure`·스트리밍 동일성 `test_streaming_analysis`). mutagen 상호운용·원본 exe dB 대조는 오염 방지를 위해 `_local/manual_checks/`(git 제외)에서 로컬 수동 실행.

### 10.2. 확정된 정책·결정 (구현 중 새로 정해진 것)

로드맵 단계·2 원칙에 이미 있는 결정(디코더/샘플레이트 예외=2.1)은 반복하지 않는다. 아래는 작업하며 새로 확정된 what(결정 + 핵심 근거).

- **저샘플레이트 계수 = 공개 표준값 전사(독립 구현 판단)**: 공식 사양은 44.1k·48k 계수만 수치로 주고 그 외는 변환만 기술. 원본 동일 응답 재설계는 비공개 target 곡선·scipy 미지원(yulewalk 등가 없음)으로 원리적 불가. 2.1 최우선이라 여러 독립 구현이 사양처럼 공유하는 표준 계수 수치만 차용(코드 독립, 저작권 비대상 수치). 1차 출처(ReplayGain 공개 사양) 병기, 44.1k·48k 자기검증.
- **허용오차 0.1dB(합의)**: 저샘플레이트에서 디코더 차이(mpg123 vs ffmpeg)+히스토그램 양자화로 실측 최대 0.06dB. 완화가 아니라 디코더가 항구 예외인 프로젝트에서 불가피 편차의 실측 상한. 계수 오류(수 dB)는 확실히 걸러짐.
- **표시Only 정책 통일**: `api.analyze_file` 은 Volume·Track Gain·3색 clip 을 재현하되, (1) Track Gain 제수는 정밀값 `5*log10(2)`, (2) 스텝 반올림은 적용 경로와 동일한 `db_to_steps` 로 통일 → "표시=실제 적용 결과" 항상 일치. clip 판정식(`peak×2^(steps/4)>32767`)은 저작권 비대상 수식이라 차용, 원본 코드는 미차용.
- **8단계 아키텍처: 코어 직접 import(subprocess 아님)**: 원본은 VB↔C 언어차로 exe subprocess·stdout 파싱했으나 우리는 같은 Python 이라 코어 직접 import(subprocess 는 언어 제약의 산물, 재현 대상 아님). 진행률·취소·에러를 파이썬 객체로.
- **8단계 MVP 범위(합의)**: 컬럼 = 파일명(전체 경로)/Volume/Track Gain/clip(3색)/Curr Max Amp. 목표 89dB 기준 재현. 클립 = auto-clip 끔 + 지정값 적용 + 판정은 표시로만. 초기 MVP 제외였던 Album·트레이·로그·언어메뉴·정렬저장·우클릭팝업은 이후 전부 구현 완료. 미구현 잔여는 Constant Gain·Max No-clip(10.3 보류).
- **취소 정책(합의)**: 청크 경계에서 취소 + 진행 중 ffmpeg 즉시 kill. decode 계층이 청크마다 should_cancel 확인, proc.kill() 후 DecodeCancelled → 워커가 정상 취소로 구분. scan/apply 순수 파이썬 순회도 `_CALLBACK_INTERVAL` 마다 should_cancel(취소 시 GainCancelled, 파일 write 이전이라 원본 무손상).
- **스트리밍 분석(곡 전체 PCM 미적재)**: `TrackAnalyzer` + `decode_pcm_streaming` — 청크를 흘려 누적, 결과는 통짜와 **비트 단위 동일**(diff=0 실측, `test_streaming_analysis` 고정). 근거: lfilter zi 청크 연속, RMS 자투리 이월, peak 는 필터 전 원샘플 abs. 통짜 함수는 짧은 곡·CLI·테스트용 존치.
- **다국어 위치(합의)**: CLI 는 영문만, 화면 다국어화는 GUI 계층 tr()/번역파일.
- **i18n 구현 세부 확정**: 재현 대상은 동작(런타임 교체·로케일 폴백·수동 전환·영속화)이지 원본 제약이 아님(2.2). 지원 = en(원문, .qm 없음=폴백) + ko(`gaindb_ko.qm`). 초기 언어=QSettings 우선, 없으면 로케일 감지. Language 메뉴(QActionGroup)에서 고르면 영속화+즉시 전환, LanguageChange→retranslate 로 헤더 포함 실시간 갱신. 세부: (1) SPL 라벨은 `(ReplayGain 89 dB 기준)` 축약, 상세는 툴팁. (2) 컬럼 헤더는 `columns.py` 상수를 `QT_TRANSLATE_NOOP("FileTableModel", …)` 로. (3) 비-QObject 는 `QCoreApplication.translate(...)`. (4) OK/Cancel 등 표준 위젯은 `qtbase_<lang>.qm` 로드. (5) 로그 내용은 영문 고정. 빌드: lupdate → .ts 채움 → lrelease.
- **AVD 연결(확정)**: 병합 시 다운로드 후 별도 단계로 api 호출(실시간 결합 아님). 폴더 넘기면 곡별 결과 반환.
- **진행 UI 정책(합의)**: 적용(scan+apply, 디코딩 없는 순회)은 순식간이라 진행바는 **분석 단계만** 0→100% 표시, 적용은 진행률 생략(취소만 계속 연결). 앨범은 2단계(분석→적용)라 진행바 1회·상태바 카운트 2회 왕복.
- **clear_result 는 tag_scanned 유지**: 태그 삭제·Clear Analysis 후 상태 = "태그 없는 파일 추가"와 동일이므로 Track Analysis 대상. clear_result 는 result·status 만 리셋, tag_scanned=True 유지.
- **Track Gain steps==0 정책**: 대상 행을 steps 무관 전부 워커에 넘기고 태그 기록 판단은 코어에 위임 — steps==0 이라도 태그가 없거나 dirty 면 코어가 기록(`-r` 동작), 최신이면 디코딩 없이 no_change.
- **로그 기능 정책**: 원본 로그 동작을 관찰해 독립 재현. (1) on/off UX = 체크박스 노출(enabled/path 분리). (2) dB 표기 = 정밀값 `FIVELOG10TWO`. (3) 타임스탬프 = ISO 8601 고정. (4) Album Analysis Log = 그룹당 한 줄. 구현: `gui/logging.py`(Qt 비의존) + `logs_dialog.py` + main_window 배선. 로그 실패는 상태바 안내만. QSettings `logs/*` 영속화.
- **트레이 기능 정책**: 원본 트레이 동작을 관찰해 독립 재현. Options 체크(기본 꺼짐, QSettings `tray/*`) + 최소화 시 창 숨김·트레이 아이콘, 좌클릭/더블클릭/팝업 Restore, 팝업 Exit. X 는 실제 종료(트레이 안 감). macOS 는 자동 트레이 이동만 비활성. 아이콘 `assets/GainDB.png`.

### 10.3. 현재 상태 · 완료 이력 · 다음 할 일

- **테스트 fixture 합성 전환 — 코드 완료 / tests 저작권 감사 일부 미완.** 저작권 음원(Debussy·10cm)을 없애고 `tests/_gen_fixtures.py`(합성 생성기, git 공개)가 고정 시드 신호에서 13종 fixture 를 생성하도록 전환 완료. 산출물은 `_local/test_audio/`(git 제외). 전체 테스트 139건 PASS, skip=0(전환 전 82 skip).
  - [완료·커밋] `_gen_fixtures.py` 신규 — 대역제한(200~3000Hz) 노이즈 + 다구간 진폭 포락선 + 좌우 비대칭 + 최고구간 톤 보강. parse_file 로 mpegver/sr/nchan/granule/global_gain 검증. 44.1k 계열은 `_ROUNDTRIP_SAFE`(min≥8, max≤247)로 음수스텝 round-trip 안전 보장. 실측 max=210(255 아님 — 인코더 특성상 이 신호로는 210 이 상한. "정확히 255"는 옛 fixture 의 우연한 성질이었을 뿐 테스트가 요구한 조건이 아님).
  - [완료·커밋] `_support.py` — KNOWN_FIXTURES 중립 이름(test_gain_44k/test_gain_48k + 파생 11종), MP3_DIR 기본 `_local/test_audio/`. 로직 불변.
  - [완료·커밋 f4ed749] `test_clamp_reversibility.py` 신규 — 255/0 클램프 비가역성 값 단위 검증 9건(fixture 무관, 항상 실행). fixture max 가 210 이라 자연히 안 타는 클램프 경계를 코드로 직접 커버.
  - [완료·커밋 c6e28d8] 8개 테스트 파일 곡명→중립 이름 치환(총 25건): test_album/test_analysis_integration/test_cli_misc/test_clip_integration/test_recalc_decode_skip/test_roundtrip_options/test_tag_integration/test_useid3_migration.
  - [**미완 — 다음 세션 최우선**] tests 트리 A/B/C 전수 저작권 감사(8.8). 지금까지 한 것은 (C) 중 '옛 곡명 치환'뿐. 각 테스트 파일 docstring·주석의 (B) clean-room, (C) '원본 …' 심볼·함수명·뉘앙스는 아직 미감사. 확실히 위험 없음은 `__init__.py`(빈 파일)·`test_clamp_reversibility.py`(신규 작성)뿐. 나머지 16개는 "곡명 치환 완료, 전수 감사 미완". 시작점: `Select-String -Path "tests\*.py" -Pattern "clean-room","원본"` 로 규모 파악 → 다른 소스 감사(2.3)와 동일하게 "mp3gain 과 동일한 결과/동작"으로 중립화 → 139건 재통과 → 커밋 → LICENSE_REVIEW.md #23 를 실제 소거완료로 기록.
  - [미완] `_gen_fixtures.py` 의 `_LEGACY_NAMES`(옛 곡명 삭제 목록) 잔존 — 기능적 필요, fixture 안정화 후 제거/주석화 검토.
  - [완료·커밋 aa26ec4/이번] CLAUDE.md 본문 갱신: 트리에 신규 2파일 등재 + 추적 파일 수 실측 47 반영 + test_audio 합성 설명, 9항 클램프 fixture 서술(max=210 rt-safe) 정정, 10.1 검증 인프라(139건 PASS·skip=0·fixture 합성) 갱신 완료.
  - [참고] 전체 테스트 실행 시간 184초(전환 전 5.5초) — skip 되던 디코딩·분석이 전부 실행되는 것이라 정상. 필요 시 시드 길이(_SEED_SECONDS=2.5) 단축으로 최적화 여지.

**현재 상태.** 1~7단계 완료, 8단계 GUI MVP + 후순위 기능 전부 실사용 완료. 라이선스 정리(완전 독립 노선·Apache 2.0) 진행 중: LICENSE/NOTICE 추가, CLAUDE.md·LICENSE_REVIEW.md 완전 독립 노선으로 정리, `_local/` 격리 완료, 파일별 저작권 위험 전수 감사(8.8) 착수. GUI 는 Track/Album 분석·게인, 우클릭 팝업, 취소, 스트리밍, 컬럼폭·정렬 저장, 로그, 트레이, 다국어(영문/한국어 실시간 전환)까지 실사용 가능.

**완료 이력(계열별 요약. 개별 커밋은 git log).**
- 1~7단계 코어·CLI: 프레임/분석/디코드/태그/CLI/샘플레이트/라이선스 검토(상세 10.1).
- 8단계 GUI MVP: 리스트 UX·Track 분석/게인·취소·스트리밍·우클릭 팝업·성능 인덱스.
- 앨범 계열: 코어(`_apply_one_album_file`+스트리밍 api)·리스트뷰 3컬럼·analyze/apply 워커·진행 UI 2안. "앨범 peak 이동은 공유 `change_gain_and_tag` 가 구조적 보장" 확증.
- 컬럼폭·정렬·창 기하 QSettings 영속화 + Reset Column Widths + 전 컬럼 Interactive·가로 스크롤·헤더 세로 구분선.
- 로그 기능(`gui/logging.py`·`logs_dialog.py`·배선·`test_logging.py` 12건, 정책 10.2).
- 트레이 기능(리소스 헬퍼·아이콘·minimize-to-tray·Exit quit, 정책 10.2).
- i18n: 진입점 배선·UI tr() 래핑·Language 메뉴·한국어 .ts/.qm·SPL 라벨 축약·영문 표기 통일·QT_TRANSLATE_NOOP 헤더·로그 다이얼로그·qtbase 로 OK/Cancel(정책 10.2).
- 라이선스 정리(진행 중): 완전 독립 노선 확정, Apache 2.0, LICENSE/NOTICE, `_local/` 격리, 파일별 감사(8.8).

**다음 할 일(남은 것만).**

- **파일별 저작권 위험 전수 감사(8.8) — 진행 중.** `_local/LICENSE_REVIEW.md` 부록 A.1 표 순서대로 소스 트리 전 파일을 하나씩 세션 열어 감사·소거·기록. 우선순위: mp3gain_cli.py → analysis.py → id3.py → tag.py → frame.py → writer.py → api.py → gui/* → 문서/테스트. 매 파일 수정 후 테스트 130건 통과 확인·커밋.
- **README + LICENSE 헤더.** 감사 완료 후 README(프로젝트 소개·설치·ffmpeg 안내·라이선스 배지) 작성, 필요 시 각 소스 파일에 Apache 2.0 짧은 헤더 추가.
- **공개 전 최종 점검.** 히스토리에 위험 파일 없음 재확인(완료), 전체 빌드·테스트, AVD 의 `gaindb/` 사본 동기화, 전문가(변호사) 검토(2.3).
- **후순위 기능 GUI — 잔여 없음.** 남은 것은 아래 보류 항목뿐.
- **실클릭 회귀 — 반복 점검 체크리스트로 존치.** 오디오 경로(decode/scan/apply)를 실제로 건드리는 변경이 있을 때, 취소 후 `audio_body_sha256` 로 원본 무결성을 재확인한다.
- **보류·점검 항목(성격이 달라 완료로 옮기지 않고 존치).**
  - **비가역(255 클램프) 사전 경고 — 보류 확정(합의).** 원본은 경고 없이 조용히 클램프. 재론하려면 원본 이탈 감수 가치의 합의 필요.
  - **steps==0 곡 태그 재확인 비용 — 최적화 보류.** 체감 지연 시 모델 `has_tag` 플래그로 최신 태그 곡만 사전 제외 고려.
  - **Constant Gain(`-g`/`-l`) GUI — 최후순위 보류(축소 아님).** 코어(`apply_gain`) 완비, 슬라이더 다이얼로그+워커만 얹으면 됨.
  - **Max No-clip(`-x` 계열) GUI — 보류(축소 아님).** 계산 뼈대는 `-k` 로 코어에 존재.
- **CLAUDE.md 유지.** 단계 완료 시 10.3 만 갱신. 2 핵심 원칙을 약화시키는 압축은 금지(2·8 참조).