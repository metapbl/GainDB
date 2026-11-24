# v1.4.0 — 두 줄 머리글·좁은 창 · 머리글 잘림 수정 · 선택 메뉴 · 언어 시스템 기본값 · Release
Status: active | 시작: 2026-11-24 | 근거: PRD §2.1 1.4 작업, F11 (D110~D115)

목표: 6개 언어 모두 첫 창 폭을 1.3.1보다 20% 이상 줄이고(머리글 두 줄), 언어를 바꾸거나 다시 실행해도 머리글이 잘리지 않게 한다. 원본 GUI의 선택 메뉴 3개와 언어 "시스템 기본값"을 넣고 v1.4.0을 게시한다.

근거:
- 시안(Q075): 줄바꿈 규칙과 폭 공식으로 en 1090→825, ko 1090→758, zh 1090→742, ja 1214→958, es 1288→920, ru 1265→924
- 잘림 원인: 컬럼 폭을 언어에 맞추는 곳이 처음 실행(`_build_central`)과 열 너비 초기화뿐. 언어 변경(`changeEvent` LanguageChange)과 저장 폭 복원(`_restore_settings`)은 맞추지 않음
- 원본 `frmMain.frm` 파일 메뉴: Select All Files(Ctrl+A)·Select No Files(Ctrl+N)·Invert selection(Ctrl+V)

구조:
- `gui/columns.py` — 머리글 줄바꿈 함수(언어 규칙), Path\File 기본 폭 300
- `gui/model.py` — `headerData`가 두 줄 머리글을 돌려줌
- `gui/main_window.py` — 컬럼 기본 폭 공식, 언어 변경·복원 때 좁은 컬럼 넓히기, Maximizing 켤 때 창 넓히기, 선택 메뉴, 언어 메뉴 System default
- `gui/i18n.py` — 저장된 언어 지우기
- `gui/translations/*` — 새 문구
- `tests/test_gui_layout.py` (새 파일), `tests/test_i18n.py`
- `README*.md`, `docs/images/*-v3.png`, `gaindb/__init__.py`, `pyproject.toml`, `docs/release-notes-1.4.0.md`

전역 제약:
- 코어(`gaindb/`)는 바꾸지 않는다(버전 번호만). AVD 동기화 대상 없음
- 수치·태그·CLI 출력은 그대로. 보이는 모양만 바뀐다
- 테스트는 tempfile 사본, 사용자 QSettings를 건드리지 않는다. 폭 비교는 같은 환경에서 1.3.1 공식으로 계산한 값과 비교한다(글꼴이 환경마다 달라 고정 숫자로 비교하지 않음)
- 새 화면 문구는 tr()과 5개 언어 번역을 같은 작업에서, ko는 작업 7에서 사용자 검수
- git push·git tag·gh release·build_release.ps1 실행 전 사용자 확인 (D041)
- 커밋은 작업마다 1개, 작업마다 전체 테스트

## 작업
- [x] 1. 머리글 줄바꿈 함수 (wrap_header, 266건 OK) — `gui/columns.py`
  - 먼저 실패 테스트: "Track Gain"→"Track\nGain", "clip(Album)"→"clip\n(Album)", "볼륨"·"클리핑"·"トラックゲイン" 그대로, "클립(앨범)"→"클립\n(앨범)", "현재 최대 진폭"→"현재\n최대 진폭", "アルバム音量"→"アルバム\n音量", "当前最大振幅"→"当前\n最大振幅", 한글·라틴 단어 중간에서 나누지 않음
- [x] 2. 두 줄 머리글과 좁은 기본 폭 (268건 OK, 실제 글꼴 창 폭이 시안과 같음 en 825·ko 758·zh 742·ja 958·es 920·ru 924, D116) — `model.headerData`, `_default_column_width`, Path\File 300 (after: 1)
  - 기존 사용자가 새 모양을 보도록 `_LAYOUT_VERSION`을 올려 저장된 창 크기·컬럼 폭을 한 번 초기화한다 [AI]
  - 먼저 실패 테스트: 6개 언어 첫 창이 1.3.1 공식으로 계산한 폭보다 20% 이상 좁고 가로 스크롤 없음, 모든 숫자 컬럼이 머리글 긴 줄+30 이상
- [x] 3. 머리글 잘림 수정 (270건 OK) — 언어 변경·저장 폭 복원 때 좁은 컬럼만 넓힘 (after: 2)
  - 먼저 실패 테스트: en 폭에서 ru로 바꾸거나 ru로 다시 실행하면 모든 숫자 컬럼이 머리글+30 이상, 사용자가 더 넓힌 컬럼은 그대로
- [x] 4. Maximizing 켤 때 창 넓히기 (272건 OK) — `_on_toggle_maximizing` (after: 2)
  - 먼저 실패 테스트: 최대화가 아닌 기본 창에서 켜면 가로 스크롤이 없다(화면 안에서), 최대화 상태면 창 크기 그대로
- [x] 5. 선택 메뉴 (274건 OK, 새 문구 3개 5개 언어) — 파일 메뉴 Select All Files(Ctrl+A)·Select No Files(Ctrl+N)·Invert selection(Ctrl+V)
  - 먼저 실패 테스트: 파일 3개에서 선택이 3·0·(하나 선택 뒤)2개, 메뉴 위치, 단축키가 다른 키와 겹치지 않음
- [x] 6. 언어 System default (275건 OK, 새 문구 1개 5개 언어) — 언어 메뉴 맨 위 + 구분선, 고르면 저장값을 지우고 로케일 규칙으로 바로 바꿈
  - 먼저 실패 테스트: 저장 ru·로케일 ja_JP에서 고르면 바로 日本語, 저장값 없음, 다시 실행해도 日本語이고 System default 체크
- [x] 7. 번역 검수 (ko 새 문구 4개 사용자 확정 "이대로 확정" 2026-11-25, 6개 언어 캡처는 작업 2에서 확인) — 새 문구 5개 언어(작업 5·6에서 넣음), ko 사용자 검수, 6개 언어 캡처 (after: 5, 6)
- [x] 8. 버전·README (4d0479b, 275건 OK, 스크린샷 -v3, 스크린샷 스크립트 설정 분리 버그 수정, 노트 사용자 승인 2026-11-25) — 1.4.0, 6개 언어 GUI 문단(선택 메뉴·시스템 기본값), 스크린샷 -v3 다시 생성, 노트 초안(사용자 승인) (after: 2~7)
  - 확인: `test_readme.py`, readme 표준 §6 검사, 이미지 2장 각 2 MB 이하, 노트 승인
- [x] 9. 빌드·캡처 (CI 3개 OS 초록 run 45509307828 at cff5fc1 275건, pip-audit 취약점 없음, BUILD OK, zip에 .qm 5개·라이선스. 빌드 exe는 사용자 설정 언어(ko)로 확인: 두 줄 머리글·잘림 없음·스크롤 없음. es는 사용자 설정을 바꾸지 않으려고 소스 캡처로 대신) — push·CI 3개 OS, pip-audit, `build_release.ps1`, exe를 es로 띄워 머리글이 잘리지 않은 캡처 (실행 전 확인)
- [x] 10. Release (태그 v1.4.0 = cff5fc1, https://github.com/metapbl/GainDB/releases/tag/v1.4.0, zip 96466726 bytes, 2026-11-25) — 태그 v1.4.0, GitHub Release (실행 전 확인)
- [x] 11. 인수 (명세 검토: 막는 결함 없음, 지적 6건은 1.4.1로 수정 D117) — F11 인수 기준 5개, 명세 검토(대화 맥락 없는 서브에이전트에 이 파일·PRD F11·`git diff {시작 커밋}..`)

## 자체 검토
- 빠진 PRD 기능: 없음 (F11 전부, §2.1 1.4 작업 1~3. 4 scipy는 다음 계획)
- 테스트로 바꾸지 못한 인수 기준: 없음. 머리글 모양은 6개 언어 캡처로 보강
- 순서: 2 after 1 · 3, 4 after 2 · 7 after 5·6 · 8~11 순서대로
- [AI] 추가 결정: `_LAYOUT_VERSION` 올림(기존 사용자 창 크기·컬럼 폭 1회 초기화) — 작업 2에서 결정으로 기록

## 1.4.1 (작업 11 명세 검토 지적, D117)
- [x] 12. 작업 중 선택 메뉴 끄기·시작 포커스 파일 표 — `_update_action_states`, 시작 끝
- [x] 13. 언어 변경 뒤 창 넓히기 (넓어진 컬럼이 있을 때만) — Maximizing과 같은 규칙(최대화 아님, 화면 안, 스크롤 없는 폭까지)
- [x] 14. 스크린샷 스크립트 (279건 OK, README 스크린샷 바이트 동일, README.ru 문구도 수정)·레이아웃 테스트 i18n 설정 분리, 러시아어 System default "Как в системе"
- [ ] 15. 1.4.1 버전·노트(승인, D116 초기화에 창 위치·최대화 포함 명시)·CI·빌드·Release (실행 전 확인)
