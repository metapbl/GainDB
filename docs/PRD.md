# PRD — Gain dB (GaindB)

상태: approved (2026-10-25) | 단계: 5 확정 | 갱신: 2026-10-25
<!-- 상태가 approved (YYYY-MM-DD)가 되기 전에는 코드·뼈대·의존성 설치를 하지 않는다. -->
<!-- 모든 항목 끝에 출처를 단다: [U] 사용자 · [X] 기존 코드·문서 · [AI] AI 기본값. 근거 결정은 (D###). -->

## 1. 목적
- 해결할 문제: MP3 파일들의 음량을 재인코딩 없이(무손실) 고르게 맞춘다. mp3gain과 같은 결과를 내는 Python 재구현으로, Windows·macOS GUI까지 제공한다. [X] (D002)
- 사용자 (누가, 몇 명, 어떤 기기): 개발자 본인(AVD로 받은 MP3의 후속 처리) + GitHub 공개 사용자. Windows·macOS 데스크톱. [X]
- 성공 기준 (관찰 가능한 장면 하나): 폴더의 MP3를 GUI에서 Album 분석·적용하면 원본 mp3gain과 같은 dB·태그가 나오고, undo 하면 오디오가 원본과 비트 단위로 같게 돌아온다. [U] (D029)
  - "같다"의 정의: dB는 0.1dB 이내(D005), global gain 최솟값·최댓값과 적용 스텝은 정확히 같음, 태그는 `-s c -o`로 읽은 REPLAYGAIN_*·MP3GAIN_* 값이 같음(dB 필드는 0.1dB 이내), undo 뒤 audio_body_sha256 같음. 대조 대상은 CI 러너의 패키지 mp3gain(버전은 CI 로그에 기록). [AI]
- 기한과 수명 (언제까지, 다 쓰면 폐기/유지): 공개 후 계속 유지. 이후 AVD와 연계해 다기능 유틸리티로 발전. [X] (D012)

## 2. 범위
### 2.1 필수
- 무손실 음량 조정(global_gain ±N), Track/Album 분석·적용, APEv2/ID3v2 태그 읽기·쓰기·갱신·제거·undo, mp3gain 호환 CLI 옵션 전부, PySide6 GUI. [X] (D002)
- 이번 작업 (순서대로): [U] (D033, D028, D038, D039, D031)
  1. 서술 정리 — 완료 기준: 추적 파일에서 "독립 재구현", "independent re-implementation", 파생 영역에 대한 "independent implementation"이 검색되지 않는다. 계수 출처를 말하는 "여러 독립 구현이 공유하는 공개 표준 수치"는 사실이라 유지. 바꿀 문구: "mp3gain 소스를 읽고 Python으로 리팩토링한 재구현(일부 모듈은 원본 개작, LGPL 유지)". [AI]
  2. F6 ffmpeg 찾기 (§3).
  3. CI 추가 (§6) — 완료 기준: main push에서 3개 OS 작업이 모두 초록. [AI]
  4. 정식 GitHub Release — 완료 기준: GitHub Releases에 태그·릴리스 노트·Windows onedir zip이 올라가 있고 zip 안에 LICENSE·NOTICE·THIRD_PARTY_LICENSES·licenses/qt가 있다. 버전 0.6.0, 첨부물은 Windows onedir zip만(D044, D045). 릴리스 노트는 AI 초안 → 사용자 승인 후 게시. 같은 태그가 이미 있거나 빌드·라이선스 검증이 실패하면 멈추고 보고. [AI]
### 2.2 있으면 좋음
- 없음. 보류 목록(2.3)이 그 역할. [U] (D034)
### 2.3 이번에는 안 함
- AVD 연계 (다른 세션에서 진행). [U] (D032)
- 사용자가 먼저 요구하기 전까지 보류: steps==0 태그 재확인 최적화, Constant Gain GUI, Max No-clip GUI, scipy 제거(용량 절감). [X]
### 2.4 반목표 (절대 그렇게 되면 안 되는 동작)
- 타 포맷 지원. [X] (D001)
- mp3gain 기능을 합의 없이 축소·단순화. [X] (D002)
- 255 클램프 사전 경고 추가(원본 동작 이탈). [X] (D022)
- 테스트가 fixture 원본을 건드림. [X] (D019)
- 파생 사실을 부인하는 서술. [X] (D006)
### 2.5 나중을 위해 구조만 준비
- AVD가 소비할 공유 진입점 `gaindb/api.py`(analyze_file, 비파괴). [X] (D012)
### 2.6 제약 (법·라이선스·비용·개인정보)
- 전체 LGPL-2.1-or-later, 원본 저작권 헤더 6파일 고지 의무. mp3gain 소스를 읽고 리팩토링한 개작임을 밝힌다. 변호사 검토 완료. 세부는 `_local/LICENSE_REVIEW.md`(로컬 전용). [X][U] (D006, D026, D027, D025)
- ffmpeg 미동봉(사용자 설치). PySide6 LGPLv3 → exe는 onedir. [X][U] (D028, D020)

## 3. 기능
<!-- adopt: 흐름은 기존 문서, 인수 기준은 기존 테스트(tests/)에서 추출. F6은 새로 작성. -->
### F1 음량 분석 (Track/Album)
- 정상 흐름: ffmpeg로 PCM 스트리밍 디코딩 → ReplayGain(equal-loudness + RMS + 95퍼센타일) → 목표 89dB 대비 스텝 산출. Album은 히스토그램 누적. [X] (D010)
- 예외: mono는 `-ac 1` 디코딩 후 복제(3dB 버그 교훈). 취소 시 청크 경계에서 ffmpeg kill. [X] (D009)
- 상태별 동작: 완전한 태그가 있으면 재분석 때 디코딩을 건너뜀. [X]
- 인터페이스: `gaindb.api.analyze_file` (CLI/GUI/AVD 공유, 비파괴). [X]
- 인수 기준: [X]
  - Given 44.1k 스테레오 MP3 / When 옵션 없이 CLI 실행 / Then 파일은 바뀌지 않고, 제안 Track dB가 코어 분석값과 같다 (test_analysis_integration)
  - Given 32k~8k·mono MP3 / When 분석 / Then 기준값과 0.1dB 이내 (test_samplerate_expansion)
  - Given 같은 파일 / When 청크 크기를 바꿔 스트리밍 분석 / Then 히스토그램·gain·peak가 통짜 분석과 비트 단위로 같다 (test_streaming_analysis)
  - Given 완전한 게인 태그가 있는 파일 / When 다시 분석 / Then 디코딩하지 않고 같은 값을 낸다 (test_recalc_decode_skip)
- 확인 방법: 자동 테스트 [X] (D005, D019)
### F2 무손실 게인 적용·undo
- 정상 흐름: 프레임 global_gain ±N, CRC 재계산, 디코딩 불필요. [X]
- 예외: 0/255 클램프는 비가역(경고 없음, 원본 일치). 취소는 write 전 순회에서만 → 원본 무손상. [X] (D009, D022)
- 인수 기준: [X]
  - Given 스테레오·조인트스테레오·mono MP3 / When -3스텝 적용 후 undo / Then 오디오 본문 해시가 원본과 같다 (test_roundtrip_options, test_tag_integration)
  - Given global_gain 254인 프레임 / When +3 / Then 255로 잘리고 되돌려도 원래 값이 안 된다 (test_clamp_reversibility)
  - Given 적용하면 클리핑이 나는 파일 / When `-r -k` / Then 클리핑이 안 나는 만큼 낮춰 적용한다 (test_clip_integration)
  - Given 클리핑 확인 질문이 뜬 상태 / When n 또는 입력 없음(EOF) / Then 적용하지 않는다 (test_clip_integration)
  - Given mono 또는 조인트스테레오 파일 / When 한 채널만 조정(`-l`) / Then 거부한다 (test_roundtrip_options)
- 확인 방법: 자동 테스트 [X]
### F3 태그 (APEv2 기본, ID3v2 `-s i`)
- 정상 흐름: ReplayGain 표준 필드 + MP3GAIN_MINMAX/ALBUM_MINMAX/UNDO 기록·읽기·갱신·제거. [X]
- 인수 기준: [X]
  - Given 태그 없는 파일 / When `-r` 적용 / Then APE에 게인 필드가 기록되고 `-s c`로 같은 값이 읽힌다 (test_tag_integration)
  - Given APE 태그가 있는 파일 / When `-s i`로 적용 / Then ID3에 기록되고 옛 APE는 제거된다 (test_useid3_migration)
  - Given 태그가 있는 파일 / When `-s d` / Then 태그만 지워지고 오디오는 그대로다 (test_tag_integration)
  - Given 태그가 있는 파일 / When `-s c` / Then 파일은 바뀌지 않는다 (test_cli_misc)
- 확인 방법: 자동 테스트 [X]
### F4 CLI (`gaindb_cli.py`)
- 정상 흐름: mp3gain 옵션 체계 전부 재현, 영문만, recalc 비트마스크로 디코딩 스킵. [X] (D011)
- 인수 기준: [X]
  - Given `-a`와 `-r`을 함께 / When 실행 / Then Album(`-a`)이 우선한다 (test_options_parsing)
  - Given 모르는 옵션 / When 실행 / Then 경고하고 나머지를 계속 처리한다 (test_options_parsing)
  - Given `-o` / When 분석 / Then 탭 구분 형식으로 출력하고, `-s c -o`는 11열이다 (test_analysis_integration, test_cli_misc)
  - Given `-v` 또는 `-h` / When 실행 / Then 버전·사용법을 출력한다 (test_roundtrip_options)
- 확인 방법: 자동 테스트 [X]
### F5 GUI (`python -m gui`)
- 정상 흐름: 파일/폴더 목록, Track/Album 분석·게인, 우클릭(Clear Analysis/Undo/Remove Tags/Play), 취소, 컬럼 저장, 로그, 트레이, en/ko, About. [X] (D007, D013~D017, D024)
- 인수 기준:
  - Given 하위 폴더가 있는 폴더 / When 재귀 추가 / Then 확장자 대소문자와 무관하게 MP3만 모인다 [X] (test_gui_pure)
  - Given 분석된 행 / When 목표 dB만 바꿈 / Then 파일은 바뀌지 않고 Volume(=89−raw)은 그대로, 스텝만 바뀐다 [X] (test_gui_pure)
  - Given 분석된 행 / When Track Gain 적용 / Then 스텝이 0이 되고 peak가 2^(스텝/4)배로 바뀐다 [X] (test_gui_pure)
  - Given 로그 꺼짐 / When 분석 / Then 로그 파일에 아무것도 쓰지 않는다 [X] (test_logging)
  - Given 폴더의 MP3들 / When GUI에서 Album 분석·적용 후 undo / Then 적용 직후 dB·태그가 원본 mp3gain과 같고, undo 뒤 오디오가 원본과 같다 [U] (D029, 성공 기준)
- 확인 방법: 순수부는 자동 테스트. 마지막 항목은 AI가 확인: CI에서 원본 mp3gain CLI와 dB·태그·undo 해시 대조 + GUI Album 워커 offscreen 실행 결과를 CLI와 대조. [U][AI] (D038)
### F6 ffmpeg 찾기 (변경)
- 정상 흐름: PATH에서 ffmpeg·ffprobe를 먼저 찾고, 없으면 OS별 후보 폴더를 아래 순서로 본다. 동봉하지 않는다. [U] (D028)
  - Windows: `%LOCALAPPDATA%\Microsoft\WinGet\Links` → `C:\ffmpeg\bin` → `%ProgramFiles%\ffmpeg\bin` [AI]
  - macOS: `/opt/homebrew/bin` → `/usr/local/bin` [AI]
  - Linux: PATH만 (지원 대상 아님, CI용. apt는 /usr/bin에 설치) [AI]
- 예외: [AI]
  - ffmpeg·ffprobe는 같은 출처(PATH, 또는 같은 후보 폴더)에서 둘 다 찾았을 때만 쓴다. 섞지 않는다. 하나라도 없으면 다음 후보로 간다.
  - 파일은 있으나 실행이 실패하면 지금처럼 DecodeError(해당 파일만 실패).
  - 어디에도 없으면 DecodeError, 메시지에 찾아본 위치 전부.
  - ffmpeg가 필요 없는 작업(게인 적용·undo·`-s c`·`-s d`·디코딩을 건너뛰는 재분석)은 막지 않는다.
- 상태별 동작: CLI는 지금처럼 파일마다 오류를 출력하고 다음 파일로 계속, 종료 코드 1 [X] (gaindb_cli.py). GUI는 Track/Album 분석을 시작할 때 한 번 확인하고, 못 찾으면 대화상자를 한 번 띄운 뒤 분석을 시작하지 않는다(파일 미변경). [AI]
- 인터페이스: `gaindb/decode.py`에 찾기 함수(찾은 두 경로를 돌려줌, 못 찾으면 DecodeError)를 추가하고 디코딩이 이를 쓴다. GUI는 분석 시작 전에 이 함수를 부른다. `analyze_file` 등 기존 함수의 모양은 그대로. [AI]
- 인수 기준: [U][AI]
  - Given PATH와 후보 폴더 양쪽에 ffmpeg·ffprobe 있음 / When 찾기 / Then PATH의 경로를 돌려준다
  - Given PATH에는 없고 두 번째 후보 폴더에만 둘 다 있음 / When 찾기 / Then 그 폴더의 경로를 돌려준다
  - Given PATH에 ffmpeg만 있고 첫 후보 폴더에 둘 다 있음 / When 찾기 / Then 첫 후보 폴더의 두 경로를 돌려준다
  - Given 어디에도 없음 / When CLI로 파일 2개 분석 / Then 파일마다 영문 오류(찾아본 위치 포함), 종료 코드 1, 두 파일 모두 바뀌지 않는다
  - Given 어디에도 없음 / When GUI에서 Album 분석 시작 / Then 대화상자가 한 번 뜨고 README 설치 안내 링크가 있으며, 분석 워커는 시작되지 않는다
  - Given 어디에도 없음 / When CLI로 `-s c` / Then 정상 출력 (ffmpeg 불필요)
- 링크 대상: GUI 언어가 ko면 GitHub의 README.ko.md "ffmpeg 설치" 절, 아니면 README.md "Installing ffmpeg" 절. [AI]
- 확인 방법: 자동 테스트(PATH와 후보 폴더를 임시 폴더로 주입해 찾기 함수의 반환값 확인, GUI 확인은 offscreen에서 대화상자 호출 횟수 확인) + CI macOS 러너(Homebrew ffmpeg, PATH를 /usr/bin:/bin으로 줄여 Finder 실행 흉내). macOS 실기기 확인은 없음. [U][AI] (D037, D039)
## 4. 기술 결정
| 항목 | 선택 | 버린 안 (이유) | 근거 |
|---|---|---|---|
| 언어 | Python ≥3.13 | - | D023 |
| 신호처리 | numpy + scipy | - | D023 |
| 디코딩 | ffmpeg 외부 호출, PATH + 알려진 설치 위치 | mpglib 이식 (실용성) / PATH만 (macOS) | D028 |
| GUI | PySide6, 코어 직접 import | exe subprocess | D007 |
| 배포 | PyInstaller onedir | onefile (LGPLv3) | D020 |
| 라이선스 | LGPL-2.1-or-later | Apache-2.0 / MIT 혼합 | D006 |
| CI | GitHub Actions (Windows·macOS·Ubuntu), mp3gain CLI 대조 포함 | 수동 대조만 | D038, D039 |

## 5. 비기능 요구
- 실행 환경 (OS, 언어 버전, 네트워크): Windows·macOS, Python ≥3.13 (개발 PC는 3.15), ffmpeg/ffprobe는 F6대로 찾음, 네트워크 불필요. [X][U]
- 성능 (시작 시간, 반응 속도, 자원): 수 시간 곡도 메모리 폭증 없이 분석(스트리밍). [X] (D010)
- 배포 형태: GitHub 소스 + Windows exe(onedir, 로컬에서 build_release.ps1로 빌드). macOS는 소스 실행, 배포물 없음(D045). 법률 관문은 해소. [X][U][AI] (D020, D026)
- 로그 (위치, 형식, 상세 모드): GUI 로그 파일, ISO 8601, 영문. [X] (D016)

## 6. 검증과 운영
- 자동 테스트 대상 / 실기기 확인 대상과 결과 전달 방식: 코어·CLI·GUI 순수부는 unittest. 원본 mp3gain 대조는 CI에서 자동(Ubuntu·macOS의 mp3gain CLI). 실클릭 회귀(취소 후 무결성)는 수동. [X][U] (D019, D038, D039)
- CI: GitHub Actions, main push와 수동 실행. Windows·macOS·Ubuntu × Python 3.13(최소 지원). 각 러너는 ffmpeg 설치 → `tests/_gen_fixtures.py`로 합성 fixture 생성 → 전체 unittest. Ubuntu(apt)·macOS(brew)는 mp3gain을 설치해 성공 기준 대조 스크립트도 실행. mp3gain 설치 실패나 대조 불일치는 실패로 처리. GUI Album offscreen 대조 테스트는 새로 작성. [AI] (D038, D039)
- 전체 테스트 명령과 걸리는 시간: `python -m unittest discover -s tests` (139건). 약 3분 (184초, Python 3.15.1, 2026-10-25 측정, D046). [X]
- 편집 때 자동 검사 (확장자별 린터·타입 검사 명령): `.py` → `python -m py_compile <파일>`. [U] (D040)
- 위험한 명령 (실행 전 확인 대상): git push, git tag, gh release, build_release.ps1, `_local/` 삭제. [U] (D041)
- 버전 관리 (커밋 단위, 메시지 형식): 의미 단위마다 커밋, Conventional Commits, 신원 metapbl / ggoyong2@gmail.com. [X] 브랜치는 main 하나. [U] (D030)

## 7. 미결
→ `docs/discovery/OPEN.md`

## 8. 변경 이력
| 날짜 | 변경 | 근거 |
|---|---|---|
| 2026-10-24 | adopt: 기존 CLAUDE.md·README·코드에서 초안 역추출 | Q001~Q022 |
| 2026-10-25 | 질의응답 반영, PRD 검사 보완 | Q023~Q043, D026~D046 |
