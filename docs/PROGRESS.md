# PROGRESS — Gain dB (GaindB)

## 상태
- 단계: 8 구현 · 활성 계획 없음
- 버전: 1.1.2 게시 (태그 v1.1.2 = 9a6adaf) · 테스트 204건 (로컬 OK, skip 3 = mp3gain 대조 / CI 3개 OS 초록, run 42955891636), 약 2분 (.venv Python 3.15.1)
- 갱신: 2026-11-11 · v1.1.2 Release (분석 로그 행당 한 번, D076) · pip-audit 취약점 없음 · v1.1.1 Release (Re-calculate를 Options 바로 아래로, D075) · 1.1.0 exe 옵션 3개 동작·1.1.1 메뉴 위치 사용자 확인 · AVD 사본 1.1.1 동기화 확인 (AVD 94418c2, 코어 9파일·라이선스 3파일 일치)

## 다음 할 일
- AVD 사본 1.1.2 동기화 (코어는 `gaindb/__init__.py` 버전만 바뀜, D012)

## 미해결
- 없음

## 확인 대기 (사람만 확인 가능)
- 1.1.2 exe에서 같은 파일을 두 번 Track Analysis하면 분석 로그가 한 줄인지 (D076)
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
- 2026-10-25 metarche 이관: PRD 승인, 결정 46개 기록 (커밋 전)
