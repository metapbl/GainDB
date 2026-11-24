# v1.3.0 — Constant Gain · Max No-clip GUI · steps==0 건너뛰기 · Release
Status: active | 시작: 2026-11-23 | 근거: PRD §2.1 1.3 작업, F10 (D100~D107)

목표: 원본 mp3gain GUI 1.3.4의 Apply Constant Gain과 Maximizing 기능 4가지를 GUI에 옮기고, Track/Album Gain에서 변화가 없는 최신 태그 곡을 건너뛴 뒤 v1.3.0을 게시한다.

근거 (원본 GUI 1.3.4 소스, 원본 exe 실행 결과 기준):
- `frmMain.frm`: Modify Gain > Apply Constant Gain...(Ctrl+O), Analysis > Max No-clip analysis(Ctrl+M), Apply Max No-clip Gain for Each file(Ctrl+X), for Album(Ctrl+L). Max 항목 3개와 Max Noclip 컬럼은 설정 MaximizingFeatures가 켜져야 보임
- `frmOptions.frm`: "Enable "Maximizing" features" 체크, 켤 때 `frmMaximizing` 안내 창
- `frmGetGain.frm`: 슬라이더 -8~+8 스텝, dB = 스텝 × 5·log10(2)(소수 1자리), "Apply to only one channel" 왼쪽/오른쪽
- 지금 GUI: `_on_gain`(gui/main_window.py)은 대상 행을 steps와 관계없이 모두 ApplyWorker에 넘긴다. 코어가 최신 태그면 no_change로 끝낸다

구조:
- `gaindb/api.py` — Constant Gain 적용, 최대 진폭만 분석, Max No-clip 적용(곡별·앨범) GUI용 진입점
- `gui/main_window.py` — 메뉴·단축키, Maximizing 옵션·설정 저장, steps==0 건너뛰기
- `gui/dialogs/constant_gain.py` (새 파일) — Constant Gain 대화상자 / `gui/dialogs/maximizing_note.py` (새 파일) — 안내 창
- `gui/workers.py` — Constant Gain·최대 진폭·Max No-clip 워커 (기존 워커 재사용 우선)
- `gui/columns.py`, `gui/model.py` — Max Noclip 컬럼
- `gui/translations/gaindb_{ko,zh_CN,ja,es,ru}.ts/.qm`
- `tests/test_gui_gain_features.py` (새 파일), `tests/test_mp3gain_parity.py`
- `gaindb/__init__.py`, `pyproject.toml`, `README*.md`(6개), `docs/release-notes-1.3.0.md`

전역 제약:
- 코어 수치·태그 포맷·CLI 출력은 바꾸지 않는다. api 진입점 추가는 AVD 동기화 대상임을 알린다 (D012)
- 원본 C·VB 코드를 그대로 번역해 옮기지 않는다. 원본 exe는 실행 결과만 기준 (R§2)
- 테스트는 tempfile 사본에서만, 사용자 QSettings를 건드리지 않는다. 무손실 판정은 audio_body_sha256 (D019)
- 255 클램프 경고를 넣지 않는다 (D022)
- 새 항목은 주 메뉴에만(우클릭 메뉴 제외). 로그·오류 원문은 영문 유지, 새 화면 문구는 tr() (D106, D011)
- git push·git tag·gh release·build_release.ps1 실행 전 사용자 확인 (D041)
- 커밋은 작업마다 1개, Conventional Commits, 작업마다 전체 테스트
- 테스트 진입점: 코어는 `gaindb/api.py` 함수, GUI는 offscreen 주 창의 QAction 트리거

## 작업
- [x] 1. 특성화 테스트 (224건 OK, skip 3) — 바뀌지 않아야 할 현재 결과를 고정: 디코딩 분석 값이 0 스텝인 곡은 Track/Album Gain 뒤 태그가 기록되고, 태그가 온전한 0 스텝 곡은 파일 바이트가 그대로다. no-clip 켬·최대 스텝<0 태그 곡은 낮춰진다 — `tests/test_gui_gain_features.py`
  - 확인: 새 테스트가 지금 코드에서 통과
- [x] 2. steps==0 건너뛰기 (원본 GUI 조건, D107, 229건 OK, skip 3) — `gui/main_window.py > _on_gain, _on_album_gain`, 값의 출처(태그 스캔/분석)를 행에 남김 (after: 1)
  - 참고: Album Gain 씨앗은 이번 세션의 Album 분석 결과뿐이고 태그 스캔은 Album 값을 씨앗으로 쓰지 않으므로(`_on_album_gain`), D107의 Album 조건은 걸리는 곡이 없다. Track만 바뀐다
  - 먼저 실패 테스트: 태그 스캔 값이 0 스텝인 곡은 워커 경로 목록에 없고, 태그 항목 일부가 빠져도 파일 바이트가 그대로다. 1의 테스트는 그대로 통과
  - 확인: 전체 테스트 통과
- [x] 3. 코어 진입점 (234건, CI 3개 OS 초록 run 45189213103 at c61c233 · 첫 CI에서 CLI `-x` 태그 차이 발견해 수정, D108·T22) — `gaindb/api.py`에 `apply_file_constant_gain`(양 채널·한 채널), `analyze_file_max_amp`(최대 진폭만, `max_noclip_steps` 포함). 원본 GUI는 Max No-clip 적용을 곡마다 `/g N`(앨범은 묶음 최솟값)으로 하므로 별도 적용 진입점 없이 Constant Gain 경로를 쓴다. 로컬 원본 exe는 DLL이 없어 실행 불가(0xC0000135)
  - 먼저 실패 테스트: 결과가 CLI `-g 3`, `-l 1 -2`, `-x`와 같다. mp3gain이 PATH에 있으면 원본과 대조(`test_mp3gain_parity.py`)
  - 확인: 전체 테스트 통과, CI mp3gain 대조 초록
- [x] 4. Constant Gain GUI (240건 OK, skip 4. 새 문구 12개는 5개 언어 AI 번역까지 넣음, ko 검수는 7에서) — Modify Gain > Apply Constant Gain...(Ctrl+O), 대화상자, 워커 (after: 3)
  - 먼저 실패 테스트: +3 적용 결과가 CLI `-g 3`과 같고 Undo로 원래 audio_body_sha256, 한 채널 -2가 `-l 1 -2`와 같음, 0 스텝은 아무것도 안 함
  - 확인: 테스트 통과
- [x] 5. Maximizing 옵션·Max No-clip analysis·Max Noclip 컬럼 (247건 OK, skip 4. 컬럼 이름은 원본대로 "Max Noclip Gain", 값은 최대 스텝×1.505 dB. 컬럼 수가 바뀌어 기존 사용자의 저장된 컬럼 폭은 한 번 기본값으로 돌아가고, 저장된 정렬 번호도 같은 조건으로 무시) — 기본 꺼짐, 켤 때 안내 창, 설정 저장 (after: 3)
  - 컬럼 위치는 원본 순서(Track 묶음 뒤, Album 묶음 앞)를 따르고 저장된 컬럼 폭·Reset Column Widths가 깨지지 않는지 확인
  - 먼저 실패 테스트: 꺼짐이면 메뉴 3개·컬럼 숨김, 켜면 보이고 재시작 뒤 유지. 분석 뒤 Max Amp·Max Noclip 칸이 채워지고 음량 칸은 그대로, 값이 CLI `-x`와 같음
  - 확인: 테스트 통과
- [x] 6. Max No-clip 적용 (254건 OK, skip 4. 원본 GUI exe는 `_local`에 소스만 있고 CLI exe도 DLL이 없어 로컬 대조 불가 → 바탕인 `-x`·`-g`는 CI mp3gain 대조로 확인됨, 적용 규칙은 원본 소스 MaxNoClipGain·GroupMaxNoClipGain 기준) — for Each file(Ctrl+X), for Album(Ctrl+L), 최대 진폭이 없으면 먼저 구함 (after: 5)
  - 먼저 실패 테스트: 앨범 사본 3개에서 적용 스텝·태그가 원본 exe 실행 결과(또는 3의 진입점 기대값)와 같고 클리핑 없음
  - 확인: 테스트 통과, 원본 GUI exe로 같은 사본을 처리한 결과와 한 번 대조(로컬)
- [x] 7. 번역 (작업 4~6에서 문구마다 5개 언어 165개 완료, ko 새 문구 28개 사용자 검수 "이대로 확정" 2026-11-24, test_i18n·번역 검사·가로 스크롤 테스트 통과) — 5개 언어 .ts/.qm, ko는 사용자 검수 (after: 4, 5, 6)
  - 확인: `test_i18n.py` 통과(미번역 0, 자리표시자·단축 문자 일치), 6개 언어 첫 창 가로 스크롤 없음, ko 검수 결과
- [x] 8. 버전·README (407638a, 254건 OK, `-v` 1.3.0, 노트 사용자 승인 2026-11-24) — 1.3.0, 6개 언어 README 기능 절에 Constant Gain·Maximizing 설명, 노트 초안(사용자 승인). 스크린샷은 다시 만들지 않는다(D106)
  - 확인: `gaindb_cli.py -v` 출력 1.3.0, `test_readme.py` 통과, readme 표준 §6 검사, 노트 승인
- [ ] 9. 빌드·캡처 — pip-audit, `build_release.ps1`, 빌드 exe에서 Constant Gain 대화상자와 Maximizing 메뉴 캡처 (실행 전 사용자 확인)
  - 확인: pip_audit 결과, `BUILD OK`, 캡처 PNG 확인
- [ ] 10. Release — 태그 v1.3.0, GitHub Release (실행 전 사용자 확인)
  - 확인: Release에 태그·노트·zip, zip에 LICENSE·NOTICE·THIRD_PARTY_LICENSES·licenses/qt. AVD 동기화 대상 고지
- [ ] 11. 인수 — F10 인수 기준 7개 실행
  - 확인: 전체 테스트 통과, CI 3개 OS 초록 | 실기기: exe에서 Constant Gain·Maximizing 동작 확인
  - 명세 검토: 대화 맥락 없는 서브에이전트에 이 파일, PRD F10, `git diff {시작 커밋}..`을 주고 누락·요청 외 추가·잘못된 구현을 받는다

## 자체 검토
- 빠진 PRD 기능: 없음 (F10 전부, §2.1 1.3 작업 1·2. 3 scipy는 다음 계획)
- 테스트로 바꾸지 못한 인수 기준: 없음. 원본 GUI exe 대조는 자동화가 어려워 6에서 로컬 한 번 확인으로 보강
- 순서: 2 after 1 · 4, 5 after 3 · 6 after 5 · 7 after 4·5·6 · 8~11 순서대로
