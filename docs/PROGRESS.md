# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 8 구현 · 활성 계획 `docs/plans/2026-11-23-v130-gain-features.md` (1.3: F10 Constant Gain·Max No-clip GUI·steps==0 건너뛰기, D100~D108) · 작업 1~3 완료
- 버전: 1.2.0 게시 (태그 v1.2.0 = 9f2cbbe) · main은 README 스크린샷 반영(릴리스 없음, D097) · 테스트 234건 (로컬 OK, skip 4 = mp3gain 대조 / CI 3개 OS 초록, run 45189213103 at c61c233), 약 2분 (.venv Python 3.15.1)
- 갱신: 2026-11-24 · 1.3 작업 1~3: steps==0 건너뛰기(원본 GUI 조건, D107, 988eb68), api 진입점 apply_file_constant_gain·analyze_file_max_amp (c4020af), CLI `-x` 태그를 mp3gain과 일치 (D108, c61c233)
- 2026-11-23 · 1.3 범위 PRD 변경 승인·계획 승인 (Q067~Q070)
- 2026-11-23 · README 스크린샷: 생성 스크립트 `tests/_readme_screenshots.py` (fb257a3, 5526e3c), 6개 언어 Screenshots 절·이미지 -v2 (9759e43, 5526e3c), D096~D099
- 2026-11-23 · v1.2.0 Release (GUI 6개 언어, README 6개 언어·표준 구성)
- 이전: 2026-11-11 · v1.1.2 Release · AVD 사본 1.1.2 동기화 확인 (AVD 3278b23)

## 다음 할 일
- 계획 작업 4부터: Constant Gain GUI (메뉴·대화상자·워커)
- 1.3.0 뒤 다음 범위: scipy 제거 (D100, 별도 PRD 변경)
- AVD 사본 1.2.0 동기화 완료(사용자 확인). 1.3에서 api 진입점 2개와 `-x` 태그 수정이 생겨 1.3.0 뒤 다시 동기화 대상 (D012)
- 참고: README 스크린샷은 주 창이 바뀌면 AGENTS.md 명령으로 다시 만들고, 내용이 바뀌면 파일 이름 버전(-v3 등)을 올린다 (D098·D099). 생성 중 `M:` 드라이브가 잠시 보임
- 참고: 이 PC(한국어 Windows)에서 중·일 화면과 표·머리글은 한국어 글꼴로 대체 표시되고 `\`가 `₩`로 보임 (D089)

## 미해결
- 없음

## 확인 대기 (사람만 확인 가능)
- 없음
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
- 2026-10-25 metarche 이관: PRD 승인, 결정 46개 기록 (커밋 전)
