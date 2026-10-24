# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 8 구현 · 계획: docs/plans/2026-10-25-v060-release.md (active, 2026-10-25 승인) · 작업 0~7 완료, 작업 8 CI 실패 조사 중
- 버전: 0.5.1 · 테스트 150건 (로컬 OK, skip 1 = mp3gain 대조), 약 3분 (.venv Python 3.15.1)
- 갱신: 2026-10-25 · 마지막 커밋: `b65e07c ci: run tests on Windows, macOS and Ubuntu with mp3gain parity` (push됨)

## 다음 할 일
1. 작업 8 CI 초록 만들기 — 미해결 2건 해결 후 재실행. 이후 작업 9 Release, 10 인수 확인

## 미해결
- CI Ubuntu `test_clip_integration.test_prompt_yes_applies` 실패 — 단서: 프롬프트 `y`가 무시됨. 가설: ffmpeg/ffprobe가 stdin을 물려받아 먼저 읽음(`gaindb/decode.py`에 stdin 지정 없음, Windows는 재현 안 됨). run 40121876187
- CI mp3gain 대조 peak 불일치(상대 3e-6 이내, 원본끼리도 OS마다 다름) — OPEN O18, D048 재검토

## 확인 대기 (사람만 확인 가능)
- Release 전 Windows GUI 직접 클릭 1회 — 기대 결과: ffmpeg 못 찾음 대화상자 모양·링크, Album 분석·적용·undo가 정상
- 오디오 경로(decode/scan/apply)를 바꾼 뒤 취소 — 기대 결과: 취소 후 audio_body_sha256이 원본과 같음
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
