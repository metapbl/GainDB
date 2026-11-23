# README 스크린샷
Status: active | 시작: 2026-11-23 (계획 시작 커밋 dc14d79) | 근거: PRD §2.1 README 스크린샷 작업, §5 (D096~D098)

목표: 저장소 스크립트 한 번으로 Album 분석을 마친 주 창의 라이트·다크 PNG가 `docs/images/`에 다시 만들어지고, 6개 언어 README의 기능 절 바로 뒤 `## Screenshots`에 그 두 장이 라이트 왼쪽·다크 오른쪽으로 보인다. 릴리스는 하지 않는다.

구조:
- `tests/_readme_screenshots.py`(새로) — 생성 스크립트. `render(out_dir) -> list[Path]`와 명령줄 진입점. `tests/_gui_capture.py`처럼 임시 INI QSettings·임시 폴더·합성 fixture를 쓰고, 창은 `grab()`으로 직접 렌더한다
- `tests/test_readme_screenshots.py`(새로) — 생성 결과 검사
- `tests/test_readme.py` — Screenshots 절과 이미지 링크 검사 추가
- `docs/images/main-light.png`, `docs/images/main-dark.png`(새로)
- `README.md`, `README.{ko,zh-CN,ja,es,ru}.md` — `## Screenshots` 절
- `AGENTS.md` — 명령 절에 생성 명령 한 줄

전역 제약:
- GUI·코어 코드(`gui/`, `gaindb/`)는 바꾸지 않는다. 필요해 보이면 멈추고 묻는다
- 사용자 QSettings·fixture 원본을 건드리지 않는다 (임시 INI, 임시 사본, T19)
- 화면에 로컬 경로·사용자 이름·실제 파일 이름이 없다. GUI 언어는 en (D098)
- 이미지 파일당 2 MB 이하. 내용이 바뀌면 파일 이름에 `-v2` 등을 붙이고 링크도 바꾼다 (D098)
- git push 전 사용자 확인 (D041). 릴리스·태그 없음 (D097)
- 커밋은 작업마다 1개, Conventional Commits, 작업마다 전체 테스트

시험 접점: `tests/_readme_screenshots.render(out_dir)`가 돌려준 PNG 파일들과, 렌더 직전 창의 Path\File 컬럼 표시 문자열. README는 `tests/test_readme.py`처럼 파일을 직접 읽는다.

## 작업
- [x] 1. 스크린샷 생성 스크립트 — `tests/_readme_screenshots.py > render` (두 테스트 실패 확인 후 통과, 전체 219건 OK. 상대 경로로 `Album\01 Sample.mp3`만 보임. 실제 앱 글꼴(_apply_platform_font) 사용, 한국어 Windows에서 표·머리글이 시스템 글꼴이라 `\`가 `₩`로 보여 생성 스크립트에서만 표·머리글에 앱 글꼴 지정(테마 바꿀 때마다). offscreen은 글꼴이 없어 README 이미지는 실제 플랫폼에서 생성. PNG 두 장 눈 확인 2026-11-23)
  - 먼저 실패 테스트 `tests/test_readme_screenshots.py::ReadmeScreenshotsTest::test_render_writes_light_and_dark` — 임시 폴더에 render 하면 `main-light.png`·`main-dark.png` 두 파일이 생기고, 각 2 MB 이하이며, 이미지 크기가 0이 아니다
  - 같은 파일 `::test_rows_show_no_local_path` — 렌더 직전 표의 Path\File 컬럼 문자열에 임시 폴더 경로·사용자 이름(`os.path.expanduser("~")`의 마지막 이름)·드라이브 문자가 없고, 모든 행이 Album 분석 결과(앨범 dB)를 가진다
  - 방법: 작업 폴더를 임시 폴더로 옮기고 상대 경로(`Album\01 Sample.mp3` 꼴)로 넣는다. 모델이 절대 경로로 바꿔 경로가 보이면 GUI를 고치지 말고 멈추고 보고한다. 샘플 파일 이름은 합성 fixture를 `01 Sample.mp3`~ 꼴로 복사한 것
  - 확인: 두 테스트 통과, 만든 PNG 두 장을 열어 경로·이름이 안 보이는지 눈으로 확인, 전체 테스트 통과
- [x] 2. 이미지 생성·README 6개 언어 (after: 1) — `docs/images/main-{light,dark}.png`, `README*.md`, `AGENTS.md`
  - 먼저 실패 테스트 `tests/test_readme.py::ReadmeTest::test_screenshots_section` — 6개 README 모두 기능 절 바로 다음 `##`가 스크린샷 절이고, 그 안의 `<img src>`가 `docs/images/main-light.png`·`main-dark.png` 순서이며 두 파일이 있고 각 2 MB 이하, alt가 비어 있지 않다. 상대 링크 검사에 `src="..."`도 포함
  - 생성 명령 `.venv\Scripts\python.exe tests\_readme_screenshots.py docs\images` 실행 → README 절 작성 (라이트 왼쪽·다크 오른쪽 표, 언어별 alt). AGENTS.md 명령 절에 생성 명령 추가
  - 확인: 테스트 통과, readme 표준 §6 검사(§7 항목: 이미지 존재·2 MB 이하·alt·마지막 화면 변경 뒤 재생성·이미지에 금지 정보 없음·제3자 자산 없음), 전체 테스트 통과 → test_screenshots_section 실패 6건 확인 후 통과, 이미지 27KB씩·alt 6개 언어, `##` 12개·배지 4개 6개 파일 일치, 이미지는 GUI 변경 없는 현재 코드로 생성, 제3자 자산 없음, 전체 220건 OK (2026-11-23)
- [ ] 3. 인수 — PRD §2.1 README 스크린샷 작업 완료 기준
  - 확인: 전체 테스트 통과, push 확인 후 CI 3개 OS 초록, GitHub에서 README 이미지 표시 확인(사용자)
  - 명세 검토: 이 계획, PRD §2.1 README 스크린샷 작업·§5, `git diff dc14d79..`만 준 하위 에이전트의 결과

## 자기 검토
- 빠진 PRD 기능: 없음 (§2.1 README 스크린샷 작업 1·2)
- 테스트로 못 바꾼 인수 기준: "GitHub에서 이미지가 보인다"는 push 뒤 사용자 확인. "이미지에 금지 정보가 없다"는 경로 문자열 테스트 + 눈 확인
- 인수 기준별 테스트 이름: 생성 → `test_readme_screenshots::test_render_writes_light_and_dark`, 경로 없음 → `::test_rows_show_no_local_path`, README 절·링크 → `test_readme::test_screenshots_section`·`test_relative_links_exist` (T19)
- 순서 의존: 2는 1 뒤, 3은 2 뒤
- 코어 변경 없음 → AVD 동기화 대상 아님
