# v1.1.0 — 원본 GUI 옵션 3개 · CLI -p 수정 · Release
상태: active | 시작: 2026-11-10 | 근거: PRD §2.1 1.1 작업, F8 (D070~D074)

목표: GUI 옵션 메뉴에 원본 mp3gain GUI의 날짜 유지·Track Gain 클리핑 방지·태그 재계산을 넣고, CLI `-p`가 게인 적용 때도 원래 날짜를 지키게 고친 뒤 v1.1.0을 게시한다.

근거 (원본 GUI 1.3.4 `frmMain.frm`, 원본 exe 실행):
- Preserve file date/time(`mnuKeepTime`, 설정 PreserveFileDate): 적용·undo·태그 제거에 `/p`
- Don't clip when doing Track Gain(`mnuDontAddClipping`, 설정 TrackNoClip): 적용 스텝 = min(제안 스텝, MaxNoclipMp3Gain). 제안이 0이어도 MaxNoclip < 0이면 낮춘다. MaxNoclip = floor(4·log2(32767/CurrMaxAmp)), CurrMaxAmp 없으면 0. CLI `-k`와 다름
- Tags > Re-calculate(`mnuReCalcTags`, 설정 ReCalculateTags): 추가할 때 태그를 읽지 않음, 분석에 `/s r`
- 원본 `changeGain`(mp3gain.c)은 게인 쓰기 전 날짜를 저장해 끝나면 복원한다. GaindB CLI는 `-p`를 줘도 게인 적용 뒤 날짜가 바뀐다(사본 확인). 원인: 날짜 저장이 태그 쓰기 시작에만 있고 게인 쓰기(writer.apply_gain) 앞에는 없음

구조:
- `gaindb/writer.py`, `gaindb/apply_gain.py`, `gaindb/tag.py` — 게인 쓰기 전 날짜 저장·끝난 뒤 복원
- `gaindb/api.py` — apply·undo·remove에 save_timestamp, Track 적용에 no-clip
- `gaindb_cli.py` — `-p`를 게인 쓰기까지 전달
- `gui/main_window.py`, `gui/workers.py` — 옵션 메뉴 3개, 설정 저장, 워커 전달, 재계산 때 태그 스캔 생략
- `gui/translations/gaindb_ko.ts/.qm` — 새 문구
- `gaindb/__init__.py`, `pyproject.toml`, `README*.md`, `docs/release-notes-1.1.0.md`

전역 제약:
- 코어 수치·태그 포맷·CLI 출력은 바꾸지 않는다(-p 날짜 동작만 원본에 맞춘다). 코어 변경은 AVD 동기화 대상임을 알린다 (D012)
- 테스트는 tempfile 사본에서만, 사용자 QSettings를 건드리지 않는다. 무손실 판정은 audio_body_sha256 (D019)
- 원본 "Ignore (do not read or write tags)"·Max No-clip GUI는 범위 밖 (D070, PRD §2.3)
- 로그·오류 원문은 영문 유지 (D011). 새 화면 문구는 tr()과 ko 번역을 같은 작업에서
- git push·git tag·gh release·build_release.ps1 실행 전 사용자 확인 (D041)
- 커밋은 작업마다 1개, Conventional Commits, 작업마다 전체 테스트

## 작업
- [x] 1. CLI `-p` 수정 (CI mp3gain 대조는 push 뒤 확인) — 코어 쓰기 경로, `gaindb_cli.py`
  - 먼저 실패 테스트: 날짜를 2020-01-01로 맞춘 사본에 `-r -c -p`, `-r -c -p -s s`, `-a -c -p`, `-u -p` → 날짜 그대로. `-p` 없으면 바뀜
  - 확인: 테스트 통과, CI mp3gain 대조 테스트(test_preserve_time_matches) 초록, audio_body_sha256·태그 값 기존과 같음
- [ ] 2. 날짜 유지 옵션 — Options > Preserve file date/time
  - Track/Album Gain·Undo·Remove Tags에 전달. 설정 저장, 기본 꺼짐
  - 먼저 실패 테스트: 옵션 켜고 GUI 적용·undo·태그 제거 → 날짜 그대로
  - 확인: 테스트 통과
- [ ] 3. Track Gain 클리핑 방지 — Options > Don't clip when doing Track Gain
  - 원본 GUI 식. Album Gain에는 적용하지 않는다
  - 먼저 실패 테스트: 클리핑 나는 사본에서 적용 스텝 = MaxNoclip, 제안 0·MaxNoclip<0인 경우도 낮춤, 옵션 끄면 기존과 같음
  - 확인: 테스트 통과
- [ ] 4. 태그 재계산 — Options > Tags > Re-calculate (do not read tags)
  - 켜면 파일 추가 때 태그 스캔을 하지 않아 적용 때 태그 값을 씨앗으로 쓰지 않는다
  - 먼저 실패 테스트: 태그 있는 사본 추가 → 값 칸 빈칸, Track Gain이 디코딩해 계산
  - 확인: 테스트 통과
- [ ] 5. 버전·문서 — 1.1.0, README 옵션 설명, 노트 초안(사용자 승인)
  - 확인: `gaindb_cli.py -v` 출력 1.1.0, 노트 승인
- [ ] 6. 빌드·캡처 — pip-audit, `build_release.ps1`, 빌드 결과 다크·라이트 캡처(테마 1.4.0 확인)
  - 확인: pip_audit 결과, PNG 확인, 앱 코드에 THEME_SHOT 없음
- [ ] 7. Release — 태그 v1.1.0, GitHub Release (실행 전 사용자 확인)
  - 확인: Release에 태그·노트·zip, zip에 LICENSE·NOTICE·THIRD_PARTY_LICENSES·licenses/qt. AVD 동기화 대상 고지
