<!-- metarche -->
# Gain dB (GaindB)

MP3 음량을 재인코딩 없이 분석·조정하는 도구. mp3gain 소스를 읽고 Python으로 리팩토링한 재구현(LGPL-2.1-or-later). 상세는 docs/PRD.md

## 구조
- `gaindb/` — 코어(프레임 파서·writer·분석·디코드·태그·api). 버전 단일 출처는 `gaindb/__init__.py`
- `gaindb_cli.py` — mp3gain 호환 CLI (영문만)
- `gui/` — PySide6 GUI, 코어를 직접 import
- `tests/` — unittest 스위트, `_gen_fixtures.py`가 합성 fixture 생성
- `_local/` — 원본 mp3gain 소스·exe, fixture, 라이선스 검토 문서 (git·배포물 제외)
- 파일별 역할과 흐름: docs/REFERENCE.md R§1

## 명령
- fixture 생성: `.venv\Scripts\python.exe tests\_gen_fixtures.py` (ffmpeg 필요, 산출물은 `_local\test_audio\`)
- 전체 테스트: `.venv\Scripts\python.exe -m unittest discover -s tests` (작업마다 실행)
- 실행: `.venv\Scripts\python.exe gaindb_cli.py -h` · `.venv\Scripts\python.exe -m gui`
- 편집 때 자동 검사: `.claude/hooks/check.ps1`이 실행 (`py -m py_compile`)
- 릴리스 빌드: `pwsh -File build_release.ps1` (실행 전 확인)

## 이 프로젝트의 규칙
- MP3 전용. mp3gain과 결과(동작·태그 포맷·출력·수치)를 일치시키고, 기능을 빼거나 단순화하려면 먼저 사용자와 합의한다 (D001, D002)
- 서술: "mp3gain 소스를 읽고 리팩토링한 개작". "독립 구현/재구현", "clean-room", 파생 부인 문구 금지. 원본 저작권 헤더 6파일의 고지를 지우지 않는다 (D006, D027)
- 원본 C 코드를 그대로 번역해 옮기지 않는다. 원본 exe는 실행 결과만 기준으로 쓴다 (R§2)
- 테스트·검증은 tempfile 사본에서만. fixture 원본 경로를 명령에 직접 쓰지 않는다. 무손실 판정은 audio_body_sha256 (R§4 T3)
- 255 클램프에 경고를 넣지 않는다(원본 동작) (D022)
- 보류 목록(PRD §2.3)은 사용자가 요구하기 전에 제안하지 않는다
- 코어(`gaindb/`)를 바꾸면 AVD 사본 동기화 대상임을 사용자에게 알린다 (D012)
- 커밋 신원은 metapbl / ggoyong2@gmail.com. Conventional Commits, main 브랜치 하나 (D030)
- PowerShell로 파일을 쓸 때는 BOM 없는 UTF-8 (`>`는 UTF-16으로 씀) (R§5)

## 문서 지도
- `docs/PRD.md` — 무엇을 왜 (승인본. 바꾸려면 /metarche discover)
- `docs/PROGRESS.md` — 상태·다음 할 일 (머리는 세션 시작 때 자동 주입)
- `docs/REFERENCE.md` — 근거·외부 사양·함정 대장. 필요한 절만 검색해 읽는다
- `docs/plans/` — 작업 계획 (체크박스)
- `docs/discovery/` — DECISIONS는 결정 확인용, QA_LOG는 검색만
- `_local/LICENSE_REVIEW.md` — 라이선스 검토 상세 (로컬 전용, 라이선스 작업 때만)

## 작업 기록
- 작업을 끝내면 계획 파일의 체크박스를 갱신한다. 세션을 마칠 때 docs/PROGRESS.md 머리 부분을 갱신하고 /metarche wrap을 제안한다.
- 관련 없는 작업으로 넘어갈 때는 /clear를 제안한다.
- 새 결정은 `docs/discovery/DECISIONS.md`에, 반복된 실수의 원인은 REFERENCE 함정 대장에 적는다.
- PRD 변경 중(`상태: changing`)에는 docs/ 밖을 수정하지 않는다 (훅이 막는다).

## 압축 시 보존
- 압축할 때는 진행 중인 계획 파일 경로, 수정한 파일 목록, 확인 명령, mp3gain 대조 결과를 보존한다.
