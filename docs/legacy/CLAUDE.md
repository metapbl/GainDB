# Gain dB — Claude 컨텍스트 파일

> 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하는 컨텍스트 파일.
> 첫 메시지에 본 파일(CLAUDE.md)을 첨부한다(자세한 방법은 "6. 새 세션 시작법" 참조).

---

## 1. 프로젝트 정체성

- **표시 이름**: Gain dB / **기술 이름(폴더·저장소·패키지)**: `GaindB`
- **성격**: MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구. mp3gain 과 결과(동작·태그 포맷·출력·수치)를 일치시키는 **mp3gain 기반 Python 재구현**이다. 일부 모듈은 원본 C 소스의 개작이며 원본과 같은 LGPL-2.1-or-later 로 배포한다(원칙 상세는 2 참조).
- **범위**: **MP3 단독 전용**. 무손실 게인 기법이 MP3 고유 구조라 타 포맷에 원리적으로 적용 불가(3 참조).
- **위치**: AVD(AV_Downloader)로 "MP3 지정" 다운로드한 음원의 음량을 고르게 맞추는 **후속 단계 도구**. 단독으로도 동작.
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\GaindB`
- **협업 모델**: 1인 개발자 + AI 페어 프로그래밍. 로컬 Git. GitHub 오픈소스 공개(LGPL-2.1-or-later, https://github.com/metapbl/GainDB).
- **Git 커밋 신원(필수 규칙)**: 모든 커밋은 반드시 아래 신원으로 한다. 새 환경(샌드박스·새 PC·CI)에서 작업을 시작하면 커밋 전에 반드시 `git config user.name`/`user.email` 을 확인·설정한다. `genspark_dev@genspark.ai`, `metapbl@users.noreply.github.com` 등 다른 주소로 커밋되면 안 된다(발견 시 해당 커밋을 올바른 신원으로 재작성).
  ```
  git config user.name "metapbl"
  git config user.email "ggoyong2@gmail.com"
  ```
- **장기 비전**: GaindB(코어+CLI) 완성 후 PySide6 GUI 를 얹어 Windows·macOS 크로스플랫폼 프로그램으로 만든다. 나아가 기존 AVD 프로젝트(https://github.com/metapbl/AVD)와 연계해 다기능 유틸리티로 발전시키는 것이 큰 그림이다. **연계 구도(확정)**: GaindB 를 독립 리포로 공개하고 GaindB 가 정본(canonical)이며, AVD 는 GaindB 의 `gaindb/` 코어를 소비하는 쪽이다. 수정은 항상 GaindB 에서 먼저 한다(정본 우선). GainDB 는 LGPL-2.1-or-later 이므로 AVD 가 `gaindb/` 코어를 소비할 때는 LGPL 의무(고지·해당 모듈 소스 제공·교체 가능성)를 함께 이행해야 한다(소비 방식 결정 시 재검토). 소비 방식(소스 vendoring vs pip 의존)은 연계 착수 시점에 결정한다. 당면 목표는 공개 후 유지와 마무리이며, AVD 연계는 이후 단계다.

## 2. 핵심 원칙 (최우선 · 어떤 압축·개정에서도 약화 금지)

프로젝트 전체를 관통하는 세 원칙이며 서로 한 몸이다: mp3gain 호환성, mp3gain 기반 개작 사실의 투명한 고지, LGPL-2.1-or-later 공개. 완료분의 how 는 압축해도, 이 원칙과 합의·미완·제약의 what 은 보존한다.

> **[2026-08 라이선스 전환]** 외부 AI 교차검토(GPT·Claude) 결과, `id3.py`·`tag.py`·`frame.py`·`writer.py`는 원본 C 소스(id3tag.c·apetag.c·mp3gain.c)의 함수 분해·자료구조·상수·관용구를 보존한 C→Python 개작(2차적 저작물)으로 판단될 가능성이 높다고 확인했다. 이에 따라 종전의 "독립 구현 + Apache 2.0" 노선을 폐기하고, 프로젝트 전체를 원본과 같은 **LGPL-2.1-or-later** 로 전환했다. 파생 파일에는 원본 저작권 고지와 변경 사항을 헤더에 명시했고, NOTICE 의 "파생 아님" 문구는 사실 고지로 교체했다. 이하 본문의 구(旧) "독립 구현·Apache" 서술은 역사적 기록으로만 읽는다.

### 2.1. mp3gain 호환성 (결과 일치)

- 원본 mp3gain 의 **기능·동작·태그 포맷·출력·옵션과 상호운용 가능하도록**, 결과(동작·태그 포맷·출력·수치)를 일치시킨다. 임의로 기능을 빼거나 단순화하지 않는다.
- "호환"은 **결과의 일치**를 뜻한다. 구현은 모듈에 따라 원본 C 소스의 개작(id3/tag/frame/writer·CLI 분기) 또는 새로 작성(analysis·decode·api·GUI)이며, 전체가 LGPL-2.1-or-later 단일 라이선스다(2.2 참조).
- 불가피하게 일부를 미루거나 예외를 두어야 할 때 **Claude 가 임의로 정하지 않는다.** 반드시 사용자와 합의하고, 그 결정을 10 진척 로그에 "축소가 아니라 합의된 예외 / 진행 중 미완"임이 드러나게 명시한다.
- 이미 합의된 예외/우선 구현(기능 축소가 아님):
  - **디코더(항구적 예외)**: PCM 추출은 원본의 `mpglibDBL` 디코더 대신 외부 도구(ffmpeg)를 호출한다. 실용성 때문이며, 구현 수단만 다를 뿐 분석 결과(라우드니스 dB)는 mp3gain 과 일치시킨다.
  - **샘플레이트(확장 완료)**: 44.1k·48k 를 먼저 구현·검증한 뒤, ReplayGain 사양의 나머지 샘플레이트(32k 및 MPEG2/2.5 계열)까지 확장·검증 완료. 계수는 공개 표준값 전사(사유·판단은 10.1).

### 2.2. 구현 성격 서술 원칙 (2026-08 전면 개정)

**종전의 "전 구성 요소 독립 구현" 원칙은 폐기했다.** 외부 AI 교차검토(GPT·Claude, 2026-08) 결과 `id3.py`·`tag.py`·`frame.py`·`writer.py`와 CLI 옵션 체계는 원본 C 소스의 함수 분해·자료구조·상수·관용구를 보존한 C→Python 개작(2차적 저작물)으로 판단될 가능성이 높다. 현재 서술 원칙:

- **파생 영역(고지 필수)**: 위 4파일 + CLI 분기. LGPL 하에서 합법적이며, 해당 파일 헤더에 원본 저작권 고지(Glen Sawyer 외)와 변경 사항 요약을 유지한다.
- **새로 작성된 영역**: `analysis.py`(numpy/scipy 벡터화, 계수는 공개 사양 수치), `decode.py`(ffmpeg subprocess), `api.py`, GUI 전체(PySide6, VB 원본 미참조). 다만 프로젝트 전체가 단일 LGPL-2.1-or-later 이므로 파일별 라이선스를 나누지 않는다.
- 결과(동작·태그 포맷·출력·수치)를 mp3gain 과 일치시킨다는 호환성 원칙(2.1)은 변함없다.

> 서술 금지어: "clean-room", "독립 구현/독립 작성"(파생 영역에 대해), "원본 코드를 포함·파생하지 않는다" 류의 부인 문구. 프로젝트 성격은 **"mp3gain 기반 Python 재구현 — 일부 모듈은 원본 개작이며 LGPL 을 유지한다"**로 서술한다. (경위·논거 상세는 비공개 라이선스 검토 문서, 2.3.)

원본 소스(C·GUI 모두)는 참고 자료로만 로컬 보관하며 git 및 배포물에서 제외한다(LGPL 상 원본 소스 재배포 자체는 합법이나, 저장소를 간결하게 유지하기 위함).

### 2.3. 라이선스 (요약)

- 코드는 **GNU LGPL v2.1 or later (LGPL-2.1-or-later)** 로 GitHub 에 공개한다. 이는 원본 mp3gain 의 라이선스와 동일하다.
- **파생 사실 고지(필수)**: `gaindb/id3.py`·`tag.py`·`frame.py`·`writer.py`와 CLI 옵션 체계는 mp3gain C 소스 기반 개작이다. 해당 파일 헤더에 원본 저작권 고지(Glen Sawyer 외)와 변경 사항 요약을 유지한다(LGPL §2(b) 변경 표시 의무). NOTICE 에 mp3gain 유래·변경 사실·소스 입수처를 명시한다. "파생하지 않았다"는 서술은 어디에도 다시 넣지 않는다.
- LGPL 의무 이행: LICENSE 에 LGPL-2.1 전문 포함, 수정판 소스는 GitHub 공개로 제공, 바이너리 배포 시 LICENSE·NOTICE 동봉(build_release.ps1 이 검증), 별도 EULA 로 LGPL 권리를 제한하지 않는다.
- 필터 계수의 1차 출처(ReplayGain 공개 사양)는 정직하게 병기하며, analysis.py 헤더에 ReplayGainAnalysis(Robinson/Sawyer) 고지를 둔다.
- 외부 의존성: ffmpeg 는 PATH 의 외부 프로세스로 호출하며 동봉하지 않는다(사용자 설치, README 안내). PySide6 는 LGPLv3. numpy·scipy 는 BSD.
- **정책·논거·의존성 라이선스 매트릭스·파일별 저작권 감사·공개 전 체크리스트는 비공개 통합 문서 `_local/LICENSE_REVIEW.md` 에 있다.** (이 파일명은 본 문서에서 여기 2.3 에만 1회 표기하고, 다른 곳에서는 "비공개 라이선스 검토 문서(2.3)"로 지시한다. 4 저장소 트리의 구조 표기는 예외.)
- 공개 배포 직전 최종 확인은 자격 있는 전문가(변호사) 검토를 남겨둔다. **AI 교차검토는 쟁점 정리용 1차 참고일 뿐 법적 책임·자격을 대체하지 못한다.**

## 3. 핵심 기술 원리

- **무손실 음량 조정**: MP3 각 프레임의 사이드 정보 안 `global_gain`(8bit) 필드를 직접 ±N 하여 음량 조절. 디코더는 `2^(gain/4)` 로 샘플을 곱하므로 1스텝 ≈ 1.5dB. 재인코딩 없음 → 무손실. **MP3 고유 구조라 타 포맷에 적용 불가**(범위를 MP3 전용으로 못박는 근거).
- **음량 분석**: PCM 으로 디코딩 후 ReplayGain 알고리즘(equal-loudness 필터 + RMS + 통계, 95퍼센타일 부근)으로 인지 음량 계산. 목표값(기본 89dB)에 맞추는 데 필요한 게인 스텝 수를 산출.
- **Track gain / Album gain** 두 모드. Album 은 곡별 히스토그램을 누적해 단일 dB 산출 후 전 곡에 동일 스텝 적용.
- **태그(mp3gain 전 기능 재현 대상)**: APEv2(기본) 또는 ID3v2(`-s i`) 태그에 다음을 기록·읽기·갱신·제거 — ReplayGain 표준 필드(`REPLAYGAIN_TRACK_GAIN`/`_PEAK`, `REPLAYGAIN_ALBUM_GAIN`/`_PEAK`, ID3 는 추가로 RVA2 프레임·`replaygain_reference_loudness`), mp3gain 고유 필드(`MP3GAIN_MINMAX`, `MP3GAIN_ALBUM_MINMAX`, `MP3GAIN_UNDO`). 게인 적용 시 일관 갱신(undo 누적, gain 에서 dB 차감, peak 에 2^(N/4) 곱, minmax 에 N 가감). undo 는 이 누적된 역방향 값으로 원복한다.

## 4. 기술 스택 · 저장소 구조

- **언어**: Python 3 (3.13/3.14 등). 프레임 파서·writer 는 순수 표준 라이브러리(외부 의존성 없음).
- **신호처리**: numpy + scipy (필터·RMS·통계).
- **MP3 디코딩(PCM 추출)**: ffmpeg 직접 호출(2.1 합의된 항구적 예외). PATH 호출(동봉 안 함, 사용자 설치).
- **GUI**: PySide6 (Qt for Python, LGPLv3). Windows·macOS 크로스플랫폼. AVD 프로젝트와 스택 일치(향후 병합 대비). 기존 `gaindb/` 코어 + CLI 위에 얹는 프런트엔드(코어 재작성 없음).
- **가상환경**: venv (`.venv`).

루트: `C:\Users\ggoyo_zhxlvdr\GaindB` (구조가 바뀌면 이 트리와 10 진척 로그를 함께 갱신한다.)

GaindB/
├─ gaindb/                 # 코어 패키지 (순수 로직 + 분석)
│  ├─ __init__.py          # 버전·이름 단일 출처(__version__·PROGNAME). 버전업 시 여기만 수정(10.1)
│  ├─ frame.py             # 프레임 파서: _BitReader, 헤더 파싱, global_gain 읽기
│  ├─ writer.py            # global_gain ±N 무손실 적용 + CRC 재계산
│  ├─ decode.py            # ffmpeg/ffprobe 로 MP3→PCM (스트리밍 포함)
│  ├─ id3.py               # ID3v2 태그(RVA2 + TXXX) 읽기/쓰기
│  ├─ tag.py               # APEv2 태그(전 필드 + undo)
│  ├─ analysis.py          # ReplayGain 분석(Track/Album), dB→스텝 변환
│  ├─ api.py               # 비파괴 analyze_file (CLI/GUI/AVD 공유 진입점)
│  └─ apply_gain.py        # 게인 적용 로직(수동/auto/album)
├─ gaindb_cli.py           # 통합 CLI 진입점(mp3gain 호환 옵션 체계)
├─ gui/                    # PySide6 프런트엔드(독립 구현)
│  ├─ __init__.py
│  ├─ __main__.py          # 진입점: QApplication, i18n 배선
│  ├─ main_window.py       # 메인 창: 리스트·분석/게인·우클릭·취소·트레이·Help/About 배선
│  ├─ model.py             # Qt 테이블 모델(FileTableModel)
│  ├─ columns.py           # 컬럼 정의(QT_TRANSLATE_NOOP 헤더)
│  ├─ workers.py           # QThread 워커(분석/게인/앨범, 진행·취소)
│  ├─ logging.py           # 로그 파일 기록(Qt 비의존)
│  ├─ i18n.py              # 다국어 인프라(런타임 전환·로케일 폴백)
│  ├─ resources.py         # 아이콘 등 리소스 헬퍼(gui/assets/ 기준)
│  ├─ assets/
│  │  └─ GainDB.png         # 트레이·앱 아이콘(패키지 내부, wheel 포함)
│  │  └─ GainDB.ico         # exe 빌드용 아이콘(PyInstaller, wheel 무관)
│  ├─ dialogs/
│  │  ├─ __init__.py
│  │  ├─ logs_dialog.py    # 로그 설정 다이얼로그
│  │  └─ about_dialog.py   # About 다이얼로그(라이선스·서드파티 고지)
│  └─ translations/        # 다국어 리소스
│     ├─ .gitkeep
│     ├─ gaindb_ko.ts      # 한국어 번역 소스
│     └─ gaindb_ko.qm      # 한국어 번역 컴파일본
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
├─ README.md              # (공개) 영문 소개·설치·사용법·라이선스
├─ README.ko.md           # (공개) 한국어 소개·설치·사용법·라이선스
├─ pyproject.toml         # 프로젝트 메타·의존성·빌드 설정
├─ GainDB.spec            # PyInstaller onedir 빌드 레시피(exe 배포용)
├─ build_release.ps1      # 릴리스 빌드 스크립트(clean→빌드→라이선스 복사·검증)
├─ licenses/              # (공개) exe 동봉용 Qt 라이선스 전문 고정본
│  └─ qt/                 #   LGPL-3.0.txt·GPL-3.0.txt(gnu.org 정본, 빌드 시 산출물로 복사)
├─ requirements.txt       # 런타임 의존성 목록(numpy·scipy·PySide6)
├─ LICENSE                # GNU LGPL v2.1 전문
├─ NOTICE                 # mp3gain 유래·변경 사항·의존성 사실 고지
├─ THIRD_PARTY_LICENSES   # 의존성(numpy·scipy BSD / PySide6 LGPLv3) 라이선스 고지
├─ CLAUDE.md              # 이 컨텍스트 파일
├─ .gitignore
├─ .vscode/                # 에디터 설정(git 제외)
└─ _local/                 # 원본 참고 소스·저작권 음원·수동 검증(git·배포물 제외)
   ├─ mp3gain/             #   원본 C·VB GUI 소스(사양·동작 참고용)
   ├─ manual_checks/       #   원본 exe 결과 대조 등 수동 검증(파일 구성은 로컬 사정)
   ├─ LICENSE_REVIEW.md    #   (비공개) 라이선스 정합성 점검 + 파일별 저작권 감사 통합 문서(2.3)
   └─ test_audio/          #   합성 fixture(_gen_fixtures.py 가 생성, git·배포물 제외)

git 이 추적하는 것(= GitHub 공개 대상)은 위 트리에서 `_local/`·`.vscode/`·`__pycache__/`·`.venv/` 를 제외한 파일들이다(`git ls-files` 실측). 원본 참고 소스와 저작권 음원은 전부 `_local/` 아래로 격리되어 저장소·배포물에 포함되지 않는다. 원본 exe 는 코드가 아니라 실행 결과만 검증 기준으로 쓴다(2.2 의 "관찰된 동작 차용").

## 5. 원본 참고 자료

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `_local/mp3gain/src/` 에 보관**. git·배포물 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- **원본 Windows GUI(MP3GainGUI)는 VB 로 작성된, CLI `mp3gain.exe` 를 호출하는 프런트엔드**다. 소스를 로컬에 보관(git·배포물 제외). GUI 관련 작업에서 화면 구성·동작을 관찰·참고하되 코드는 옮기지 않는다(2.2).
- **이 미러의 `.c` 는 크롤 불가**(`application/octet-stream` MIME). 그래서 C·VB 소스는 로컬 보관 + 사용자가 붙여넣어 제공. Claude 가 크롤로 가져오려 시도하지 말 것.
- 원본 exe 는 코드가 아니라 실행 결과만 검증 기준으로 쓴다(2.2 의 "관찰된 동작 차용"). 원본 exe dB 대조는 `_local/` 의 수동 검증 스크립트로 로컬 실행.

## 6. 새 세션 시작법

새 세션은 맥락이 비어 있으므로, 첫 메시지로 필요한 문맥을 압축해 전달한다.

- **항상 첨부**: 본 파일(CLAUDE.md)을 첫 메시지에 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다. 이것만으로 프로젝트 정체성·원칙·구조·진척(10)이 전달된다.
- **작업 종류에 맞는 자료만 추가로 붙인다**:
  - 원본 동작·사양을 봐야 하는 작업(파서·분석·태그·CLI 호환) → 해당 원본 `.c`/`.h` 의 필요한 함수·구간(5 참조, 사용자가 붙여넣음).
  - GUI 작업 → 관련 `gui/*.py` 현재 본문(Claude 가 디스크를 직접 못 읽으므로), 필요 시 원본 GUI 화면 관찰 메모.
  - 감사 대상 `.py` 리팩터링·저작권 감사 → 그 파일 본문.
  - 라이선스·저작권 감사 관련 작업일 때만 비공개 라이선스 검토 문서(2.3)를 함께 첨부한다.
- **검색 도구**: 최신 정보(라이브러리·표준 확인) 용도로만 쓴다. 원본 소스 입수에는 쓰지 않는다(5).
- **진행 원칙 재확인**: Claude 는 설계·진단을 코드보다 먼저 하고(8.2), 파일 반영은 터미널 명령/코드블록으로 감싼다(8.4). 완료분은 세션 끝에 10.2~10.5 에 반영한다(7 "이 파일 관리").

## 7. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell 7.6.x). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만. (GUI 는 macOS 동작도 목표.)
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits(`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: `>` 리다이렉션은 UTF-16 LE BOM 으로 쓴다. 파일 쓰기는 BOM 없는 UTF-8 을 명시한다(`Out-File -Encoding utf8NoBOM`, 또는 한글 포함 시 `.NET` `UTF8Encoding($false)` + `WriteAllText`). 신규 파일은 `Resolve-Path` 대신 `Join-Path`(존재하지 않는 경로도 처리).
- **이 파일 관리**: 컨텍스트 파일은 짧게 유지한다. 진척이 생기면 10.2~10.5 만 갱신하고, 끝난 단계의 세부 구현 설명은 한두 줄로 압축한다. **단, 2 핵심 원칙을 약화시키는 방향으로는 압축·수정하지 않는다** — 완료된 것의 how 는 압축, 합의·미완·제약의 what 은 보존.

## 8. Claude 응답 규칙 (진행 순서대로)

실제 협업 흐름은 조사·진단 → 원칙 합의 → 설계 → 코드 확인 → 코드 제시 → 디스크 반영·커밋 순이다. 아래 규칙도 그 순서를 따른다.

### 8.1. 범위·원칙 고수

- **범위**: MP3 전용이다. 타 포맷 지원 제안은 하지 않는다(무손실 게인은 MP3 `global_gain` 기법이라 원리적으로 타 포맷 적용 불가).
- **mp3gain 호환 + 독립 구현**: 원본 기능을 임의로 빼거나 단순화하지 않는다(2.1). 무언가를 미루거나 예외로 두려면 먼저 사용자와 합의하고 10 에 명시한다. 사용자가 제공한 원본 C·VB 소스는 사양·동작 이해 목적으로만 읽고 코드를 그대로 옮기지 않는다(2.2). 알고리즘·비트 레이아웃·필터 계수·태그 포맷·UI 동작 같은 공개 사양만 차용해 독립 재작성한다.

### 8.2. 설계·진단이 먼저

코드보다 설계·진단·합의가 앞선다. 코드 블록을 보내기 전 "코드를 보내드릴까요?" 라고 한 박자 묻고, 동의 후 다음 응답에서 제시한다.

### 8.3. 코드 제시 단위

- 변경이 **함수 2개 이하**에서만 일어나고 모듈 최상위를 안 건드리면 → 변경된 함수를 개별 코드 블록으로 **함수 단위 발췌**.
- 그 외(함수 3개 이상·최상위 변경·새 함수·시그니처 변경) → **파일 전체**.
- 어느 경우든 코드 블록 바깥에 변경 지점을 한 문장으로 명시.

### 8.4. 파일 반영은 반드시 코드블록 또는 터미널 명령으로

파일(`.py`·`.md`·`.gitignore` 등)에 반영할 내용은 맨몸 텍스트로 흘려보내지 않고 둘 중 하나로 감싼다.

- **파일 전체 신규·교체** → here-string 터미널 명령: 코드 전체를 리터럴 here-string 으로 감싸 BOM 없는 UTF-8 로 저장. 사용자가 파일을 직접 열지 않고 VS Code 터미널에 붙여넣어 엔터만 치면 저장되게 한다. (리터럴 here-string 이라 백틱·달러·따옴표 안전. 단, 본문에 줄 맨 앞이 종료 구분자인 줄이 없어야 함 — 제시 전 확인. 신규 파일은 `Join-Path` 로 경로 생성.)
- **국소 수정·삽입/교체 조각** → 코드 펜스로 감싼 발췌. Claude 가 파일 전체 최신본을 정확히 보유하지 못하면 통짜 교체가 다른 부분을 훼손할 수 있으므로, 국소 수정은 통짜 교체보다 조각 발췌를 우선한다.

### 8.5. 터미널 명령 동봉

파일을 수정·추가·삭제하는 코드를 제시할 때는 디스크 반영·커밋 명령을 같은 응답에 함께 제시. 기본 흐름 (1) `git add <파일>` (2) `git status` (3) `git commit -m "..."`. 환경은 PowerShell, cwd=루트.

### 8.6. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 있으면 바깥 펜스는 안쪽보다 백틱을 하나 더 쓴다(안쪽 3개 → 바깥 4개, 그 안에 또 있으면 5개).

### 8.7. 서식

- 불릿은 대시 + 공백 1칸, 하위 불릿은 부모 기준 2칸 들여쓰기.
- 헤더 번호(깊이 2까지)는 **다른 곳에서 참조되는 섹션(2·8·10)에만** 붙인다. 나머지 최상위 섹션은 번호 없이 산문·불릿으로 둔다.
- 과한 볼드·리스트 남용 지양, 산문 우선.

### 8.8. 저작권 위험 전수 감사 절차

파일별 세션에서 소스 트리를 하나씩 검토해 저작권 위험을 소거한다. **소스 트리(코어·CLI·GUI·tests) 전 파일 감사 완료** — 절차·판정 기준·파일별 기록은 비공개 라이선스 검토 문서(2.3). 새 소스 파일 추가 시 같은 절차(식별 A/B/C → 중립화 → 테스트 통과 → 커밋 → 그 문서에 기록)를 적용한다.

## 9. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 프레임 파서의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함(프레임 파서·샘플레이트 확장에서 해결·검증 완료).
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain·255-gain 프레임은 클램프로 비가역**: `gain==0` 이면 ±N 으로 안 바뀌고(하한 유지), `gain==255` 에 +N 하면 255 로 클램프되어 초과분이 소실된다(상한). round-trip 완전복원은 경계를 벗어나지 않는 방향으로 적용할 때만 보장된다. 통합 테스트 round-trip 은 음수 스텝 먼저(-3) 후 복원(+3 또는 undo). 합성 fixture(`_gen_fixtures.py`)는 44.1k 계열 max global_gain=210(min≥8)으로 음수 방향이 안전하다. 255 클램프 자체의 비가역성은 값 단위 테스트(`test_clamp_reversibility`)가 직접 검증한다.
- **mono 분석 경로 주의(3dB 버그 교훈)**: ffmpeg `-ac 2` up-mix 는 mono 를 각 채널 1/√2 감쇠시켜 라우드니스가 정확히 3dB(≈10·log10 2) 낮게 나온다. mono 는 ffprobe 로 채널 수를 조회해 `-ac 1` 로 원진폭 디코딩 후 코드에서 좌우 복제해야 한다.
- **표시 수식 3건(원본 실측 대조로 확정)**: (1) **Volume = 89 − raw**(현재 실제 음량, 목표 무관). (2) **적용 후 shift 부호는 하향**: raw 를 `−steps×DB_PER_STEP` 로 낮춘다(`+` 로 하면 Track Gain 이 0 으로 수렴 안 함). (3) **적용 후 peak(curr_max_amp)도 함께 이동**: `×2^(steps/4)` 갱신 후 clip 재판정. 누락하면 목표 왕복 시 거짓 clip 이 뜬다. 목표만 바꾸는 `recompute_target` 은 파일 미변경이므로 peak 를 건드리지 않는다.
- **타 포맷 적용 불가**(8.1) / **원본 코드 직접 번역 금지**(2.2) / **원본 기능 임의 축소 금지**(2.1).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 소스는 로컬 보관 + 사용자가 붙여넣어 제공(5). Claude 가 크롤로 가져오려 시도하지 말 것.
- **테스트는 fixture 원본을 절대 건드리지 않는다(영구 제약, 오염 사고 재발함)**: 모든 검증·테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다. 각 테스트는 깨끗한 fixture 에서 시작한다. **원본 경로를 검증 명령에 직접 쓰지 말 것.**
- **undo 0 태그는 남는다**: 깨끗한 파일에 `-g N` 적용 후 `-u` 하면 오디오 본문은 비트 동일로 복원되지만 `MP3GAIN_UNDO 0,0` APE 태그가 남아 파일 전체 해시는 달라진다. 무손실 검증은 전체 해시가 아니라 tag_offset 까지의 오디오 본문 해시(`audio_body_sha256`)로 판정한다.
- **numpy 배열의 truthiness 평가 금지(앨범 워커 전멸 교훈)**: `arr or []`·`if arr:` 처럼 numpy 배열을 boolean 문맥에 두면 "ambiguous" 예외가 난다. 배열은 반드시 `x if x is not None else []` 로 판정한다(길이 `len(x)`, 존재 `is not None`).
- **초장시간 곡은 통짜 디코딩 금지(메모리 폭증·UI 얼음 교훈)**: 곡 전체 PCM 을 메모리에 올리면 시스템이 얼어붙는다. → 분석은 스트리밍(청크 흘림, 10.1), 취소는 청크 경계에서 ffmpeg 즉시 kill.
- **Track Gain 이중 디코딩 금지**: 씨앗(seed_db_gain·seed_peak·seed_min_gain·seed_max_gain)을 선택 주입해 유효하면 decode/analyze/scan 을 건너뛴다(결과 수치 동일). 씨앗 peak 가 None 이면 자동으로 디코딩 경로로 폴백(안전).
- **적용 단계도 취소·진행 확인 지점을 가져야 함(취소 갇힘 교훈)**: `scan_gain`·`apply_gain` 은 순수 파이썬 순회라 디코딩이 없다. 두 함수에 should_cancel/on_progress 를 `_CALLBACK_INTERVAL`(=4096) 프레임마다 확인, 취소 시 `writer.GainCancelled`. 취소 확인은 파일 write 이전 순회 단계에서만 하므로 취소해도 파일은 원본 그대로.
- **255 클램프(비가역)와 클리핑은 별개**: 클램프는 global_gain(8bit)이 255 넘어 잘려 undo 왕복이 깨지는 데이터 손실, 클리핑은 PCM 진폭이 ±32768 넘어 소리가 왜곡되는 청취 품질 문제. 임계값·발생 지점이 달라 한쪽만 생길 수 있다. mp3gain 은 클램프를 경고 없이 조용히 255 로 자르고 진행(우리 `_apply_one` 동일) — 결과 일치라 별도 경고 안 함(사전 경고는 MVP 제외, 10.5).
- **exe(--windowed)에서 자식 프로세스 콘솔 깜빡임(exe 배포 특유)**: `.py`를 콘솔에서 실행하면 ffmpeg/ffprobe 가 부모 콘솔을 물려받아 창이 안 뜨지만, PyInstaller `--windowed` exe 는 콘솔이 없어 Windows 가 자식에게 새 콘솔을 할당한다(곡마다 도스창 깜빡). → `decode.py` 의 `subprocess.run`/`Popen` 에 `creationflags=_NO_WINDOW`(`getattr(subprocess,"CREATE_NO_WINDOW",0)`, 타 OS 는 0). 코어 변경이라 AVD 사본 동기화 대상.
- **PyInstaller 아이콘은 `.ico` 필요**: exe 아이콘에 `.png` 를 주면 Pillow 없을 때 빌드 실패. `gui/assets/GainDB.png` 를 `GainDB.ico`(멀티해상도)로 변환해 리포에 두고 `.spec` 이 이를 쓴다(런타임 트레이/창 아이콘은 여전히 `.png` 사용, `resources.py` 무변경).

## 10. 진척 로그 / 정책 / 다음 시작점

### 10.1. 확정된 정책·결정

로드맵 단계·2 원칙에 이미 있는 결정(디코더/샘플레이트 예외=2.1)은 반복하지 않는다. 아래는 작업하며 새로 확정된 what(결정 + 핵심 근거).

- **저샘플레이트 계수 = 공개 표준값 전사**: 공식 사양은 44.1k·48k 계수만 수치로 주고 그 외는 변환만 기술. 원본 동일 응답 재설계는 비공개 target 곡선·scipy 미지원(yulewalk 등가 없음)으로 원리적 불가. 여러 독립 구현이 사양처럼 공유하는 표준 계수 수치만 차용(코드 독립). 1차 출처(ReplayGain 공개 사양) 병기, 44.1k·48k 자기검증.
- **허용오차 0.1dB(합의)**: 저샘플레이트에서 디코더 차이(mpg123 vs ffmpeg)+히스토그램 양자화로 실측 최대 0.06dB. 디코더가 항구 예외인 프로젝트에서 불가피 편차의 실측 상한. 계수 오류(수 dB)는 확실히 걸러짐.
- **표시Only 정책 통일**: `api.analyze_file` 은 Volume·Track Gain·3색 clip 을 재현하되, (1) Track Gain 제수는 정밀값 `5*log10(2)`, (2) 스텝 반올림은 적용 경로와 동일한 `db_to_steps` 로 통일 → "표시=실제 적용 결과" 항상 일치. clip 판정식(`peak×2^(steps/4)>32767`)은 차용, 원본 코드는 미차용.
- **8단계(GUI) 아키텍처: 코어 직접 import(subprocess 아님)**: 우리는 같은 Python 이라 코어 직접 import(원본 GUI 의 exe subprocess·stdout 파싱은 VB↔C 언어 제약의 산물, 재현 대상 아님). 진행률·취소·에러를 파이썬 객체로.
- **GUI MVP 범위(합의)**: 컬럼 = 파일명(전체 경로)/Volume/Track Gain/clip(3색)/Curr Max Amp. 목표 89dB 기준. Album·트레이·로그·언어메뉴·정렬저장·우클릭팝업·About 은 이후 전부 구현 완료. 미구현 잔여는 Constant Gain·Max No-clip(10.5 보류).
- **취소 정책(합의)**: 청크 경계에서 취소 + 진행 중 ffmpeg 즉시 kill. decode 계층이 청크마다 should_cancel 확인, proc.kill() 후 DecodeCancelled. scan/apply 순수 파이썬 순회도 `_CALLBACK_INTERVAL` 마다 should_cancel(취소 시 GainCancelled, 파일 write 이전이라 원본 무손상).
- **스트리밍 분석(곡 전체 PCM 미적재)**: `TrackAnalyzer` + `decode_pcm_streaming` — 청크를 흘려 누적, 결과는 통짜와 **비트 단위 동일**(diff=0 실측, `test_streaming_analysis` 고정). 통짜 함수는 짧은 곡·CLI·테스트용 존치.
- **다국어 위치(합의)**: CLI 는 영문만, 화면 다국어화는 GUI 계층 tr()/번역파일.
- **i18n 구현 세부**: 지원 = en(원문, .qm 없음=폴백) + ko(`gaindb_ko.qm`). 초기 언어=QSettings 우선, 없으면 로케일 감지. Language 메뉴(QActionGroup)에서 고르면 영속화+즉시 전환, LanguageChange→retranslate 로 헤더 포함 실시간 갱신. 세부: (1) SPL 라벨은 축약, 상세는 툴팁. (2) 컬럼 헤더는 `columns.py` 상수를 `QT_TRANSLATE_NOOP`. (3) 비-QObject 는 `QCoreApplication.translate(...)`. (4) OK/Cancel 등 표준 위젯은 `qtbase_<lang>.qm` 로드. (5) 로그 내용은 영문 고정. (6) About 본문도 tr() 대상이나 라이선스 명칭·파일명은 원문 유지. 빌드: lupdate → .ts 채움 → lrelease.
- **AVD 연결(확정)**: 병합 시 다운로드 후 별도 단계로 api 호출(실시간 결합 아님). 폴더 넘기면 곡별 결과 반환.
- **진행 UI 정책(합의)**: 적용(scan+apply)은 순식간이라 진행바는 **분석 단계만** 0→100%, 적용은 진행률 생략(취소만 연결). 앨범은 2단계(분석→적용)라 진행바 1회·상태바 카운트 2회.
- **clear_result 는 tag_scanned 유지**: 태그 삭제·Clear Analysis 후 상태 = "태그 없는 파일 추가"와 동일이므로 Track Analysis 대상. clear_result 는 result·status 만 리셋, tag_scanned=True 유지.
- **Track Gain steps==0 정책**: 대상 행을 steps 무관 전부 워커에 넘기고 태그 기록 판단은 코어에 위임 — steps==0 이라도 태그가 없거나 dirty 면 코어가 기록(`-r` 동작), 최신이면 디코딩 없이 no_change.
- **로그 기능 정책**: (1) on/off UX = 체크박스 노출(enabled/path 분리). (2) dB 표기 = 정밀값 `FIVELOG10TWO`. (3) 타임스탬프 = ISO 8601 고정. (4) Album Analysis Log = 그룹당 한 줄. 구현: `gui/logging.py`(Qt 비의존) + `logs_dialog.py` + main_window 배선. QSettings `logs/*` 영속화.
- **트레이 기능 정책**: Options 체크(기본 꺼짐, QSettings `tray/*`) + 최소화 시 창 숨김·트레이 아이콘, 좌클릭/더블클릭/팝업 Restore, 팝업 Exit. X 는 실제 종료. macOS 는 자동 트레이 이동만 비활성. 아이콘 `gui/assets/GainDB.png`.
- **버전·이름 단일 출처(확정)**: 정본은 `gaindb/__init__.py` 의 `__version__`·`PROGNAME`. `gaindb_cli.py`(`VERSION = __version__`)와 GUI About 이 이를 읽는다. 버전업 시 `__init__.py` 한 줄만 고치면 CLI·GUI 가 함께 따라간다. `pyproject.toml` version 은 빌드 메타라 릴리스 시 수동 갱신.
- **검증 인프라(정책)**: 통합 테스트 스위트(`tests/`, unittest, 외부 의존 없음) — `python -m unittest discover -s tests` 전부 PASS(139건, skip=0). fixture 는 `tests/_gen_fixtures.py`(합성 생성기, git 공개)가 고정 시드 신호에서 생성하며 산출물은 `_local/test_audio/`(git 제외); ffmpeg 필요. 모든 테스트는 fixture 불간섭(tempfile 사본, `FixtureGuard` 오염 감시), 무손실은 `audio_body_sha256`(오디오 본문만 해시)로 판정. 255/0 클램프 비가역성은 값 단위 테스트(`test_clamp_reversibility`)로 별도 커버. 원본 exe dB 대조는 오염 방지를 위해 `_local/`(git 제외)의 수동 검증 스크립트로 로컬 실행.
- **exe 빌드(확정)**: PyInstaller onedir + `--windowed`(`GainDB.spec`), `build_release.ps1` 이 clean→빌드→라이선스 복사·검증. onedir 로 Qt DLL 교체 가능성 유지=LGPLv3 준수(onefile 금지). 라이선스는 우리 3종 + Qt LGPL/GPL 전문(`licenses/qt/`, PySide6 6.11.1 이 텍스트 미동봉이라 고정 커밋 + 빌드 시 복사, 패키지 LICENSES 있으면 자동 복사 폴백). 근거·잔여는 비공개 라이선스 검토 문서(2.3) 1.6.1.
- **산출물 용량 절감 보류(성능)**: onedir 산출물 ≈215MB(PySide6 ~92 + scipy ~69 + numpy ~26). `.spec` excludes 로는 안전한 절감이 어려움(scipy.signal 이 fft·spatial 등에 의존해 세밀 제외 시 앱이 깨짐, Qt 모듈 제외는 훅이 DLL 을 그대로 가져와 무효). 근본 절감은 `analysis.py` 의 scipy `lfilter` 의존을 numpy 구현으로 대체(scipy 제거 → 약 145MB)해야 하나, 코어 신호처리 변경이라 mp3gain 수치 호환 재검증 필요 → 별도 작업으로 보류(10.5). collect_submodules 제거로 빌드 시간은 단축됨.

### 10.2. 완료 요약 (구현 단계 + 후속 정리)

프로젝트는 아래 단계로 나뉘어 진행됐다(작업 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다** — 2.1). **1~7단계 완료·검증 완료. 8단계 GUI 는 MVP 완료·잔여 점검 중이며, 후순위 기능(우클릭 팝업·앨범 계열·컬럼저장·로그·트레이·다국어·About)까지 완료.** 세부는 코드·git log 에 있으므로 여기선 "무엇을 완료했는가"만 남긴다. 8단계 확정 아키텍처·MVP 범위·표시 정책은 10.1, 잔여·보류는 10.3·10.5 참조.

1. 프레임 파서 + `global_gain` 읽기/쓰기(`frame.py`·`writer.py`, round-trip 바이트 동일).
2. ReplayGain 분석기(`analysis.py` — equal-loudness 필터+RMS+히스토그램+95퍼센타일). Track 은 ffmpeg replaygain 과 허용오차 이내, Album 은 혼합 검증.
3. MP3 디코딩(`decode.py` — ffmpeg/ffprobe subprocess).
4. 태그(`tag.py` APE·`id3.py` ID3v2 — read/write/remove/round-trip, scan_gain, change_gain_and_tag, auto/album, 꼬리 보존, useId3 분기).
5. CLI(`gaindb_cli.py`) — mp3gain 옵션 전부 재현. recalc 비트마스크로 디코딩 스킵(수치 일치). CLI I/O 는 영문만(다국어는 GUI 책임).
6. 샘플레이트 확장 — ReplayGain 전 샘플레이트(32k / MPEG2·2.5 계열) 코어 추가, exe 대조 min/max 전부 일치.
7. 배포 라이선스 검토 — 완료. 정책·의존성 매트릭스·파일별 감사·공개 전 체크리스트·최종 확인 절차는 모두 비공개 라이선스 검토 문서(2.3)가 관리.
8. GUI(PySide6, `gui/`, MVP 완료·잔여 점검 중) — 파일/폴더 추가·태그 스캔·자연 정렬·유니코드·리스트 UX·Track/Album 분석·게인·우클릭 팝업(Clear Analysis/Undo/Remove Tags/Play)·취소(청크 경계 즉시 kill)·스트리밍 분석(수 시간 곡)·컬럼폭/정렬 저장·로그·트레이·다국어·About 다이얼로그(라이선스·서드파티 고지). 표시값은 원본 exe 실측과 일치. `api.analyze_file`(비파괴)이 CLI/GUI/AVD 공유.

**후속 정리(완료).**

- **테스트 fixture 합성 전환** — 저작권 음원 제거, `tests/_gen_fixtures.py`(합성 생성기, git 공개)가 고정 시드에서 13종 생성(산출물 `_local/test_audio/`, git 제외). 옛 곡명 삭제 로직(`_LEGACY_NAMES`)까지 제거 완료(커밋 43d9b4e). 실측 max global_gain=210 은 round-trip 방향(-3→+3)에 무관, 255 클램프 비가역은 `test_clamp_reversibility` 가 값 단위 커버.
- **tests 저작권 전수 감사** — 코어·CLI·GUI 에 이어 tests 트리 A/B/C 전수 감사 완료(4배치). (A)(B) 없음, (C) 원본 뉘앙스·옛 스크립트명·주석 인용 중립화. exe 출력 문자열·함수명·수식·사양 수치 유지. 상세는 2.3 문서.
- **README·라이선스 헤더·의존성 파일** — 영/한 README, `pyproject.toml`·`requirements.txt`(커밋 ccc2cf1). ffmpeg 미동봉(A) 확정 + README 다운로드처·PATH 안내. SPDX 2줄 헤더를 39개 `.py` 삽입(커밋 faeb9e4).
- **버전 0.5.0 승격 · AVD 사본 동기화** — `pyproject.toml`·`gaindb_cli.py` 를 0.5.0 으로(커밋 3615722). `python -m build` 로 sdist/wheel 생성 확인(데이터 파일·LICENSE·NOTICE 동봉). AVD 의 `gaindb/` 사본 동기화 완료.
- **저작권 위생 — `M3G_ERR_*` → `ID3_ERR_*`** — id3.py 오류 코드의 mp3gain 고유 접두어(M3G) 제거, 값·로직 불변(커밋 c04ee35, 139건 PASS).
- **버전 단일 출처 정리** — `gaindb/__init__.py` 에 `__version__`·`PROGNAME` 도입, `gaindb_cli.py` 가 이를 소비(커밋 bc8707a). 정책은 10.1.
- **About 다이얼로그** — Help 메뉴에 About 추가(`gui/dialogs/about_dialog.py`, 독립 작성). ReplayGain 독립 구현 서술·Apache-2.0·서드파티(PySide6 LGPLv3 / numpy·scipy BSD / ffmpeg 외부) 고지·홈페이지 링크. 한국어 번역 완료, 버전은 단일 출처에서 표시(커밋 af750f8).
- **GitHub 공개** — https://github.com/metapbl/GainDB 에 Apache 2.0 공개, `v0.5.0` 태그. `_local/` 추적 제외 확인.
- **exe 릴리스 빌드·라이선스 동봉 자동화(완료)** — PyInstaller onedir(`GainDB.spec`) + `build_release.ps1`(clean→빌드→라이선스 복사·검증). Qt LGPL/GPL 전문을 `licenses/qt/` 에 고정하고 빌드 시 산출물 `licenses/` 로 복사(커밋: 빌드 레시피 2bcbdb3 · `.spec` 정리 aa68563). exe 환경 콘솔 깜빡임 수정(`decode.py`, CREATE_NO_WINDOW, 커밋 94bed9f, 139건 PASS). 아이콘 `.ico` 변환. 정식 Release 발행은 변호사 최종 검토 이후로 보류(10.4).

### 10.3. 진행 중

- **공개 후 유지 단계.** GaindB 는 GitHub 에 공개됨(추적 파일 + `v0.5.0` 태그). **[2026-08]** 라이선스를 Apache 2.0 에서 **LGPL-2.1-or-later** 로 전환(사유·절차는 2 서두 박스와 2.3 참조): LICENSE 교체, NOTICE 재작성(파생 사실 고지), 전 .py SPDX 교체, 파생 4파일+CLI 헤더에 원본 고지·변경 표시, README(en/ko)·pyproject·THIRD_PARTY_LICENSES·About 다이얼로그·ko 번역 갱신. `_local/` 은 추적 제외로 유출 없이 격리 확인. 현재는 소스 공개 상태이며, 정식 GitHub Release(다운로드 아카이브·릴리스 노트) 발행은 10.4 의 "변호사 최종 검토" 이후로 미뤄 둠.

### 10.4. 할 일 (남은 것만)

- **공개 전/후 최종 점검(남은 것).** 공개 전 확인 체크리스트의 마지막 미완 항목은 **자격 있는 전문가(변호사) 최종 검토**다. 절차·잔여 항목은 전부 비공개 라이선스 검토 문서(2.3)가 관리한다. 이 항목이 닫히기 전에는 정식 Release 발행을 보류한다.
- **exe 릴리스 시 라이선스 동봉 자동화(조건부 — exe 배포에 착수할 때).** PyInstaller 등으로 릴리스 바이너리를 만들 때, 빌드 산출물에 `LICENSE`·`NOTICE`·`THIRD_PARTY_LICENSES` + PySide6/Qt 의 LGPLv3/GPLv3 전문을 동봉하도록 빌드 스크립트에 자동화한다. onedir 권장(동적 링크 유지=LGPL 준수), About 의 오픈소스 고지와 함께 이행. 지금은 소스 공개 단계라 미착수 — exe 배포를 실제로 결정하는 시점에 착수하며, 그때 외부 라이선스 검토 의견을 그 단계 체크리스트로 재활용한다.
- **exe 릴리스 빌드 인프라 — 구현 완료, 실제 배포는 변호사 검토 후.** onedir 빌드·라이선스 동봉 자동화는 완료했다(10.2·10.1·2.3 1.6.1). 남은 것은 정식 Release 발행뿐이며, 이는 위 "변호사 최종 검토" 이후로 보류한다. PyInstaller onedir 는 LGPLv3(동적 링크) 준수를 유지하므로, 배포 결정 시 그대로 사용한다.
- **실클릭 회귀 — 반복 점검 체크리스트로 존치.** 오디오 경로(decode/scan/apply)를 실제로 건드리는 변경이 있을 때, 취소 후 `audio_body_sha256` 로 원본 무결성을 재확인한다.

### 10.5. 보류 항목 (사용자가 먼저 요구하지 않는 한 착수하지 않음 — 할 일이 아니다)

아래는 전부 원본 기능 축소가 아니다(2.1). 지금 안 할 뿐이며 필요하면 얹을 수 있는 상태로 남겨둔 것이다. Claude 는 이 목록을 "할 일"로 오인해 먼저 제안하지 않는다 — 사용자가 명시적으로 요구할 때만 착수한다.

- **비가역(255 클램프) 사전 경고 — 보류 확정(합의).** mp3gain 은 경고 없이 조용히 클램프하며 우리도 결과 일치를 위해 동일하게 동작한다. 경고를 넣으면 원본 동작에서 이탈하므로, 재론하려면 "원본 이탈을 감수할 가치가 있는가"의 합의가 먼저 필요하다. 넷 중 가장 강하게 닫힌 항목.
- **steps==0 곡 태그 재확인 비용 — 최적화 보류(성능).** 기능이 아니라 속도 문제. 체감 지연이 실제로 생기면 모델 `has_tag` 플래그로 최신 태그 곡만 사전 제외 고려. 지금은 불필요.
- **Constant Gain(`-g`/`-l`) GUI — 최후순위 보류(축소 아님).** 코어(`apply_gain`) 완비, CLI 로는 동작. GUI 진입점(슬라이더/입력 다이얼로그 + 워커 배선)만 안 얹은 상태.
- **Max No-clip(`-x` 계열) GUI — 보류(축소 아님).** 계산 뼈대는 `-k`(자동 클립) 경로로 코어에 존재. GUI 진입점만 안 얹은 상태.
- **scipy 의존 제거(용량 절감) — 보류(축소 아님·코어 변경).** `analysis.py` 의 `scipy.signal.lfilter` 를 numpy 구현으로 대체하면 scipy ~69MB 가 빠져 산출물이 크게 준다(215→약 145MB). 다만 코어 신호처리 변경이라 mp3gain 결과 수치 호환(2.1)을 테스트로 엄격히 재검증해야 한다. 사용자가 요구할 때만 별도 작업으로 착수.

**CLAUDE.md 유지.** 진척이 생기면 10.2~10.5 를 갱신한다(완료→10.2, 진행중→10.3, 할일→10.4, 보류→10.5). 2 핵심 원칙을 약화시키는 압축은 금지(2·8 참조).