# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 7 계획 대기 · 계획: docs/plans/2026-10-25-v060-release.md (done 2026-10-25) · 진행 중 계획 없음
- 버전: 0.6.0 (GitHub Release v0.6.0 게시) · 테스트 153건 (로컬 OK, skip 1 = mp3gain 대조 / CI 3개 OS 초록, run 40189347661), 약 2~3분 (.venv Python 3.15.1)
- 갱신: 2026-10-25 · 마지막 커밋: `6811d44 docs: record v0.6.0 device checks and update release notes` (태그 v0.6.0, push됨)

## 다음 할 일
1. AVD 사본 동기화 (D012, D050): 사용자가 별도로 진행. 대상: `gaindb/decode.py`(find_ffmpeg, stdin=DEVNULL)
2. PRD F6 갱신 완료 (Gain 버튼 확인 시점 반영)
3. 다음 계획 수립 여부 결정 (/metarche plan) — PRD §2.1 이번 작업 1~4 모두 완료

## 미해결
- 없음

## 확인 대기 (사람만 확인 가능)
- 없음 (2026-10-25 exe 실기기 확인 통과 — 계획 작업 9 결과~결과3)
<!-- head:end — 이 줄 위(40줄 이내)만 자동 주입된다. 갱신은 이 위만 고친다. -->

## 완료 기록
<!-- 한 줄씩: YYYY-MM-DD 무엇을 (커밋 hash). 50줄을 넘으면 docs/history/로 옮긴다. -->
- ~2026-08 1~8단계 완료: 프레임 파서·writer, ReplayGain 분석, ffmpeg 디코드, APE/ID3 태그, CLI, 전 샘플레이트, 라이선스 검토, GUI (이관 이전, 세부는 docs/legacy/CLAUDE.md 10.2)
- 테스트 fixture 합성 전환 (43d9b4e) · tests 저작권 감사 (1ad8015~dfabadf)
- README(en/ko)·pyproject·requirements (ccc2cf1) · SPDX 헤더 (faeb9e4)
- 0.5.0 승격 (3615722) · M3G_ERR_→ID3_ERR_ (c04ee35) · 버전 단일 출처 (bc8707a) · About 다이얼로그 (af750f8)
- exe 빌드 레시피·라이선스 동봉 (2bcbdb3, aa68563) · exe 콘솔 깜빡임 수정 (94bed9f)
- 2026-08 Apache-2.0 → LGPL-2.1-or-later 전환 (3dd1a72) · 0.5.1 (4b9abb4)
- 2026-10-25 metarche 이관·venv 재생성 (7957ae1) · 서술 정리 (78eb02f)
- 2026-10-25 F6 ffmpeg 찾기 (bda35e8~4ca74e6) · GUI Gain 버튼 확인 (7a62dae) · stdin 가로채기 수정 (dd4c421)
- 2026-10-25 mp3gain·GUI 대조 테스트 (2c9ea54, 403ceb0, 01234bf) · CI 3개 OS (b65e07c)
- 2026-10-25 v0.6.0 Release (97f4c31, 태그 6811d44) — 계획 2026-10-25-v060-release done
- 2026-10-25 metarche 이관: PRD 승인, 결정 46개 기록 (커밋 전)
