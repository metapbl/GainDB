# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 8 구현 · 활성 계획 없음 (`docs/plans/2026-11-25-v150-remove-scipy.md` 완료)
- 버전: 1.5.2 게시 (태그 v1.5.2 = b1b346f, v1.5.1 = b7f470c) · 테스트 282건 (로컬 OK, skip 4 = mp3gain 대조 / CI 3개 OS 초록, run 45557304566 at b1b346f), 약 1분 (.venv Python 3.15.1)
- 갱신: 2026-11-25 · 1.5.2 사용자 확인 뒤(미출시): 도구 모음 구분선 `@line2`(라이트 1.58·다크 1.66:1), README 스크린샷 -v5
- 2026-11-25 · v1.5.2 Release: Designarche 화면 점검 must-fix 없음, 반영 3건 — About 간격 12, Constant Gain 채널 들여쓰기·간격 12, 도구 모음 구분선 `@line`(다크 1.07→1.26:1). README 스크린샷 -v4
- 2026-11-25 · v1.5.1 Release: NOTICE·About 창에 남은 SciPy 고지 제거(1.5.0 명세 검토 지적)
- 2026-11-25 · v1.5.0 Release: scipy 제거(numpy 블록 IIR, 결과 동일, 분석 6~13% 빠름), zip 96.5→65.7 MB·폴더 225→153 MB, scipy는 requirements-dev.txt (D118~D121)
- 2026-11-25 · v1.4.1 Release: 작업 중 선택 메뉴 끄기, 시작 포커스 파일 표, 언어 변경 뒤 창 넓히기, 러시아어 System default, 스크립트·테스트 설정 분리 (D117)
- 2026-11-25 · v1.4.0 Release: F11 두 줄 머리글·좁은 창(20~33%), 머리글 잘림 수정, 선택 메뉴 3개, 언어 System default, 화면 배치 1회 초기화 (D110~D116), README 스크린샷 -v3
- 2026-11-24 · v1.3.1 Release: 게인 변경 뒤 진폭 갱신 (D109) · v1.3.0: F10 Constant Gain·Maximizing·steps==0 건너뛰기, CLI `-x` 태그 수정 (D107, D108)
- 이전: 2026-11-23 · v1.2.0 Release (GUI 6개 언어, README 6개 언어)

## 다음 할 일
- 다음 범위 정하기 (사용자 선택). 구분선 `@line2`는 다음 릴리스에 포함
- 고대비(must-fix): Windows 고대비 "밤하늘"에서 테마 색 그대로(사용자 확인 2026-11-25). Designarche 테마 `apply_theme`가 `styleHints().accessibility().contrastPreference()`(PySide6 6.12에 있음)를 안 봄 → Designarche 저장소에서 고친 뒤 GaindB는 Update 절차로 재생성. 사용자 지시 대기
- 언어 변경 뒤 창이 넓어지기만 하는 것은 D117(4) 의도 동작(사용자 문의 2026-11-25에 답함)
- AVD 사본 1.3.1 동기화 (D012): `gaindb/api.py`(apply_file_constant_gain·analyze_file_max_amp·shift_after_apply), `gaindb/apply_gain.py`(max_no_clip_steps, gain 없이 진폭만 채우기), `gaindb_cli.py`(`-x`). 1.4.x는 코어 변경 없음. 1.5.x는 `gaindb/analysis.py`(numpy 블록 IIR, scipy import 없음, 1.5.1은 docstring만, 1.5.2는 `gaindb/__init__.py` 버전만) 추가. 사용자가 AVD 세션에서 진행
- 참고: Designarche 테마는 이미 최신(Graphite/Paper 1.4.3, 생성기 출력과 `gui/theme.py`·아이콘 8개 바이트 동일, 2026-11-25 확인). 생성기 새 경로 `C:\Users\Administrator\My Projects\Designarche\designarche\scripts\generate.py`
- 참고: 1.4.0을 처음 실행하면 창 크기·위치·최대화 상태·컬럼 폭이 한 번 초기화됨(`_LAYOUT_VERSION` 2, D116). 정렬·옵션·언어는 유지
- 참고: GUI 테스트는 Windows 오프스크린(상자 글꼴)과 Linux·macOS 오프스크린(실제 글꼴)에서 폭이 다르다. 글꼴 폭에 기대는 테스트는 전제를 직접 만든다 (T24)
- 참고: README 스크린샷은 주 창이 바뀌면 AGENTS.md 명령으로 다시 만들고, 내용이 바뀌면 파일 이름 버전(-v4 등)을 올린다 (D098·D099). 스크립트는 전용 설정 이름을 써서 사용자 설정과 무관. 생성 중 `M:` 드라이브가 잠시 보임
- 참고: 이 PC(한국어 Windows)에서 중·일 화면과 표·머리글은 한국어 글꼴로 대체 표시되고 `\`가 `₩`로 보임 (D089)
- 참고: 로컬 `_local/mp3gain/src/mp3gain.exe`는 DLL이 없어 실행 불가(0xC0000135). 원본 대조는 CI에서만

## 미해결
- 없음

## 확인 대기 (사람만 확인 가능)
- 1.5.2 exe 사용자 확인 2026-11-25: 구분선 흐림(→ `@line2`로 수정), 고대비 미대응(위), 배율 150%에서 창 제목만 커짐 → 배율 150%로 둔 채 앱을 새로 켜서 내용도 커지는지 재확인 필요(커지지 않으면 must-fix). 나머지 항목은 지적 없음
- (이전) 1.3.1 exe 실제 파일 확인은 사용자 완료 2026-11-24
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- ~2026-08 1~8단계 완료: 프레임 파서·writer, ReplayGain 분석, ffmpeg 디코드, APE/ID3 태그, CLI, 전 샘플레이트, 라이선스 검토, GUI (이관 이전, 세부는 `git show 7957ae1:docs/legacy/CLAUDE.md` 10.2)
- 테스트 fixture 합성 전환 (43d9b4e) · tests 저작권 감사 (1ad8015~dfabadf)
- README(en/ko)·pyproject·requirements (ccc2cf1) · SPDX 헤더 (faeb9e4)
- 0.5.0 승격 (3615722) · M3G_ERR_→ID3_ERR_ (c04ee35) · 버전 단일 출처 (bc8707a) · About 다이얼로그 (af750f8)
- exe 빌드 레시피·라이선스 동봉 (2bcbdb3, aa68563) · exe 콘솔 깜빡임 수정 (94bed9f)
- 2026-08 Apache-2.0 → LGPL-2.1-or-later 전환 (3dd1a72) · 0.5.1 (4b9abb4)
- 2026-10-25 metarche 이관·venv 재생성 (7957ae1) · 서술 정리 (78eb02f)
- 2026-10-25 F6 ffmpeg 찾기 (bda35e8~4ca74e6) · GUI Gain 버튼 확인 (7a62dae) · stdin 가로채기 수정 (dd4c421)
- 2026-10-25 mp3gain·GUI 대조 테스트 (2c9ea54, 403ceb0, 01234bf) · CI 3개 OS (b65e07c)
- 2026-10-25 v0.6.0 Release (97f4c31, 태그 6811d44) — 계획 2026-10-25-v060-release done
- 2026-11-05 metarche upgrade U1~U4 (42186ef) · 보안 정책 D051~D056 (153b096) · pip-audit 도입 (9d604d9)
- 2026-11-10 v1.0.0 Release: Graphite/Paper 테마·UX 개선·로그 기본 경로 (태그 a386935) — 계획 2026-11-05-v100-theme-ux done
- 2026-11-11 v1.1.0 Release: CLI -p 수정 (2e1e609), GUI 옵션 3개 (34bceaf, 506037d, 8effe42), 테마 1.4.0~1.4.3 (태그 4afa542) — 계획 2026-11-10-v110-original-options done
- 2026-11-11 AVD 사본 1.1.0 동기화 확인 (AVD d6bc06c) · v1.1.1 Release: Re-calculate 메뉴 이동 (64cea24, 태그 71e4901) · AVD 사본 1.1.1 동기화 확인 (AVD 94418c2)
- 2026-11-11 원본 D067 확인(두 번 분석해도 로그 한 줄) → 분석 로그 행당 한 번 (c86784e, D076) · v1.1.2 Release (태그 9a6adaf) · 1.1.2 exe 사용자 확인 · AVD 사본 1.1.2 동기화 확인 (AVD 3278b23)
- 2026-11-20 metarche upgrade U8·U1·U6·U7 (824e874) · PRD 1.2 변경 승인 (fd91a87) · 계획 (6eef201)
- 2026-11-21 1.2 작업 1~7: 언어 표·번역 검사 (f2bb9d9) · 로케일 규칙·메뉴 (b049a58) · zh_CN (d578764) · ja (26a213a) · es (e5b97f7) · ru (47e2948) · 6개 언어 가로 스크롤 테스트 (ca5719a)
- 2026-11-21~23 1.2 작업 8~12: README 6개 언어 (5440e03, d61807e) · 1.2.0 버전·노트 (68d9437) · 빌드 (792d40b) · F9 테스트 보강 (cbb07b7, 1b15441) · v1.2.0 Release (태그 9f2cbbe)
- 2026-11-23 README 스크린샷: PRD 변경 (dc14d79) · 계획 (f188238) · 생성 스크립트 (fb257a3) · 6개 언어 절 (9759e43) · 실제 경로·-v2 (5526e3c) · 함정 T19 (aaa4e58)
- 2026-11-23~24 1.3: PRD 변경·계획 (b289ca4, 98f9382) · steps==0 건너뛰기 (1eec000, 988eb68) · api 진입점 (c4020af) · CLI `-x` 태그 수정 (c61c233, D108·T22) · Constant Gain GUI (e672880) · Maximizing·컬럼 (77b9742) · Max No-clip 적용 (fc5db35) · v1.3.0 Release (태그 6215ffd)
- 2026-11-24 1.3.1: 명세 검토 → 진폭 갱신 버그 수정 (fc5d1fc, D109·T23) · v1.3.1 Release (태그 cac4261) · 사용자 exe 실제 파일 확인
- 2026-11-24~25 1.4: PRD 변경·시안 확정 (6e31d72, Q075) · 줄바꿈 함수 (61cf034) · 두 줄 머리글·좁은 폭 (44335f5) · 잘림 수정 (e96d382) · Maximizing 창 넓히기 (093828c) · 선택 메뉴 (bebedc1) · System default (5697ffa) · README·스크린샷 -v3·스크립트 설정 분리 (4d0479b) · v1.4.0 Release (태그 cff5fc1)
- 2026-11-25 1.4.1: 명세 검토 지적 6건 (d11d634, D117) · CI 테스트 전제 수정 (040ac5b, 6b38b4d, 51a0086, T24) · v1.4.1 Release (태그 51a0086) · Designarche 테마 최신 확인
- 2026-11-25 1.5: PRD 변경·계획 (082e873, Q077·D118~D121) · scipy 대조 테스트 (b9e58d2) · numpy 블록 IIR (6896731) · 속도 최적화·측정 (5a68ae6, Q078) · requirements-dev.txt (4d9bc6e) · 문서·1.5.0 (8c3cca0) · 빌드·exe 확인 (e0a4488) · v1.5.0 Release (태그 e0a4488)
- 2026-11-25 1.5.1: 명세 검토 → NOTICE·About SciPy 고지 제거 (31d0f61) · 버전·노트 (7a01aa4) · v1.5.1 Release (태그 b7f470c) — 계획 2026-11-25-v150-remove-scipy done (d0b5ed2)
- 2026-11-25 1.5.2: Designarche 화면 점검 반영 (87e3267, 45a0b52) · 버전·노트 (b1b346f) · v1.5.2 Release (태그 b1b346f, zip 65665438 bytes)
- 2026-10-25 metarche 이관: PRD 승인, 결정 46개 기록 (커밋 전)
