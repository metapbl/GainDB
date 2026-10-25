# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 8 구현 · 계획: docs/plans/2026-10-25-v060-release.md (active, 2026-10-25 승인) · 작업 0~8 완료, 작업 9는 빌드·실기기 확인 통과, 태그·Release 대기
- 버전: 0.6.0 · 테스트 153건 (로컬 OK, skip 1 = mp3gain 대조 / CI 3개 OS 초록, run 40182562880), 약 3분 (.venv Python 3.15.1)
- 갱신: 2026-10-25 · 마지막 커밋: `7a62dae fix(gui): check ffmpeg before Gain buttons analyze unanalyzed files` (push됨)

## 다음 할 일
1. 작업 9 남은 것: `git tag v0.6.0` → 태그 push → `gh release create`(docs/release-notes-0.6.0.md, build\dist\GainDB-0.6.0-windows.zip). 이후 작업 10 인수 확인
2. AVD 사본 동기화 (D012, D050): GaindB 계획 완료 뒤에 진행. 대상: `gaindb/decode.py`(find_ffmpeg, stdin=DEVNULL)

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
- 2026-10-25 metarche 이관: PRD 승인, 결정 46개 기록 (커밋 전)
