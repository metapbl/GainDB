# REFERENCE — Gain dB (GaindB)
<!-- 필요할 때 검색해 읽는다. 참조는 R§n, 코드 위치는 파일 > 함수. -->

## R§1 아키텍처
- 흐름: 분석 = ffmpeg 디코딩(PCM, 스트리밍) → ReplayGain 히스토그램 → dB → 스텝. 적용 = 프레임 global_gain ±N(디코딩 불필요) → 태그 갱신.
- 두 경로를 혼동하지 않는다: 디코딩은 분석에만 필요하다.
- `gaindb/frame.py` — 프레임 헤더·사이드 정보 파싱, global_gain 위치 (원본 개작)
- `gaindb/writer.py` — global_gain ±N 무손실 적용 + CRC 재계산, `scan_gain`·`apply_gain` (원본 개작)
- `gaindb/decode.py` — ffmpeg/ffprobe subprocess, `decode_pcm`·`decode_pcm_streaming`, `DecodeError`·`DecodeCancelled`
- `gaindb/analysis.py` — ReplayGain(equal-loudness + RMS + 95퍼센타일), Track/Album, `db_to_steps` (Robinson/Sawyer 고지)
- `gaindb/id3.py`·`gaindb/tag.py` — ID3v2(RVA2+TXXX)·APEv2 태그 읽기/쓰기/제거, undo (원본 개작)
- `gaindb/api.py` — `analyze_file`(비파괴), `recompute_target`. CLI·GUI·AVD 공유 진입점
- `gaindb/apply_gain.py` — 게인 적용(수동/auto/album)
- `gaindb_cli.py` — mp3gain 옵션 체계, recalc 비트마스크로 디코딩 스킵 (원본 개작)
- `gui/main_window.py` — 메인 창 배선 · `gui/workers.py` — QThread 워커(TagScan/Analyze/Apply) · `gui/model.py` — FileTableModel
- `gui/i18n.py`·`gui/translations/` — en(원문)+ko(.qm), lupdate → .ts → lrelease
- `GainDB.spec`·`build_release.ps1` — PyInstaller onedir, 라이선스 복사·검증 · `licenses/qt/` — Qt LGPL/GPL 전문 고정본

## R§2 외부 사양·제약
- mp3gain 원본: https://github.com/Sound-Linux-More/mp3gain (원조 https://sourceforge.net/projects/mp3gain/). C·VB 소스와 exe는 `_local/mp3gain/`. exe는 MSYS2 UCRT64 DLL 필요(이 PC엔 없음). 원본 GUI는 VB로 CLI를 호출하는 프런트엔드 — 화면·동작만 참고.
- ReplayGain 사양(David Robinson, replaygain.org): 44.1k·48k 계수만 수치 공개, 그 외 샘플레이트는 공개 표준값 전사 (D004). 목표 89dB.
- 무손실 원리: 디코더가 샘플에 2^(gain/4)을 곱하므로 1스텝 ≈ 1.5dB. Track Gain 제수는 정밀값 5·log10(2) (D008).
- 태그 필드: REPLAYGAIN_TRACK_GAIN/_PEAK, REPLAYGAIN_ALBUM_GAIN/_PEAK, (ID3) RVA2·replaygain_reference_loudness, MP3GAIN_MINMAX, MP3GAIN_ALBUM_MINMAX, MP3GAIN_UNDO. 적용 시 undo 누적, gain에서 dB 차감, peak에 2^(N/4) 곱, minmax에 N 가감.
- ffmpeg/ffprobe: 외부 프로세스, 동봉 안 함. Windows는 `creationflags=CREATE_NO_WINDOW` (T10). 찾는 위치는 PRD F6.
- PySide6(LGPLv3)·numpy·scipy(BSD-3). exe는 onedir 필수(Qt DLL 교체 가능성 = LGPLv3) (D020).
- 원본 저작권 헤더가 있는 파일: frame·id3·tag·writer·analysis·gaindb_cli. 라이선스 상세는 `_local/LICENSE_REVIEW.md`(로컬 전용).

## R§3 설계 근거
<!-- 내용은 docs/discovery/DECISIONS.md에 있다. 여기는 색인만. -->
- D001 — MP3 전용
- D002 — mp3gain 결과 일치, 축소는 합의 후
- D004 — 저샘플레이트 계수는 공개 표준값
- D005 — 허용오차 0.1dB
- D006 — 전체 LGPL-2.1-or-later, 서술 금지어
- D007 — GUI는 코어 직접 import
- D008 — 표시=적용 일치 (db_to_steps 공용)
- D009 — 취소는 청크 경계 + ffmpeg kill, write 전에만
- D010 — 스트리밍 분석
- D011 — CLI 영문, GUI만 다국어
- D012 — GaindB 정본, AVD는 코어 소비
- D019 — 검증: 합성 fixture, tempfile, audio_body_sha256
- D020 — PyInstaller onedir
- D022 — 255 클램프 경고 안 함
- D027 — "읽고 리팩토링한 개작" 서술
- D028 — ffmpeg는 PATH + 알려진 설치 위치
- D029·D038 — 성공 기준과 CI mp3gain 대조
- D039 — CI 3개 OS
- D044·D045 — v0.6.0, Windows zip만

## R§4 함정 대장
| ID | 증상 | 원인 | 대처 | 근거 |
|---|---|---|---|---|
| T1 | mono 곡 라우드니스가 정확히 3dB 낮음 | ffmpeg `-ac 2` 업믹스가 채널당 1/√2 감쇠 | ffprobe로 채널 수 조회, mono는 `-ac 1` 디코딩 후 코드에서 복제 | legacy 9 |
| T2 | 적용 후 Track Gain이 0으로 수렴 안 함 / 거짓 clip | 표시 수식 오류: Volume=89−raw, 적용 후 raw는 −steps×DB_PER_STEP, peak도 ×2^(steps/4) | 세 식 모두 지킴. `recompute_target`은 peak를 건드리지 않음 | legacy 9, test_gui_pure |
| T3 | fixture 오염(재발) | 검증 명령에 원본 경로 직접 사용 | tempfile 사본만, `FixtureGuard` | legacy 9 |
| T4 | undo 후 파일 해시가 다름 | `MP3GAIN_UNDO 0,0` APE 태그가 남음 | 전체 해시 대신 audio_body_sha256 | legacy 9 |
| T5 | 앨범 워커 전멸, "ambiguous" 예외 | numpy 배열을 `or`/`if`에 사용 | `x if x is not None else []`, `len(x)` | legacy 9 |
| T6 | 초장시간 곡에서 시스템 얼어붙음 | 곡 전체 PCM 적재 | 스트리밍 분석, 청크 경계 취소 | D010 |
| T7 | Track Gain 이중 디코딩 | 이미 계산한 값을 버림 | seed 값 주입 시 decode 생략, seed peak None이면 폴백 | legacy 9 |
| T8 | 적용 중 취소가 안 먹음 | scan/apply 순수 파이썬 순회에 확인 지점 없음 | `_CALLBACK_INTERVAL`(4096)마다 should_cancel, write 전에만 | D009 |
| T9 | round-trip 복원 실패 | 0/255 클램프는 비가역 | 음수 스텝 먼저(−3→+3). 클램프는 값 단위 테스트로 | test_clamp_reversibility |
| T10 | exe에서 곡마다 콘솔 창 깜빡임 | `--windowed` exe는 자식에게 새 콘솔 할당 | subprocess에 CREATE_NO_WINDOW (94bed9f) | legacy 9 |
| T11 | PyInstaller 빌드 실패 | 아이콘 .png는 Pillow 필요 | `gui/assets/GainDB.ico` 사용 | legacy 9 |
| T12 | global_gain 값이 엉뚱함 | 사이드 정보 비트 오프셋이 MPEG 버전·채널 모드별로 다름 | frame.py 파서 기준, 샘플레이트 테스트로 고정 | legacy 9 |
| T13 | Linux·macOS에서 클리핑 질문에 파이프로 준 `y`가 무시됨 (Windows는 정상) | ffmpeg/ffprobe가 부모 stdin을 물려받아 키 입력용으로 먼저 읽음 | 자식 프로세스는 `stdin=subprocess.DEVNULL` (dd4c421) | test_clip_integration (CI Ubuntu) |
| T14 | 전체 테스트가 위젯 테스트에서 0xC0000409로 죽음 (단독 실행은 통과) | discover가 모든 모듈을 먼저 import하는데, test_gui_pure가 그때 `QCoreApplication`을 만들어 위젯 생성 불가 | 테스트의 Qt 앱은 offscreen `QApplication`으로 통일 | test_gui_pure, test_ffmpeg_locate |
| T15 | 편집한 Windows 경로에 `\f`·`\b` 제어 문자가 들어감 | Bash heredoc으로 넘긴 Python 문자열에서 `\\`가 `\`로 바뀜 | 백슬래시가 든 편집은 Edit 도구로. 편집 뒤 제어 문자 검사 | 작업 3 (2026-10-25) |

## R§5 환경·도구
- 개발 PC: Windows 11, PowerShell 7, Python 3.15 (`py` launcher; `python`은 스토어 별칭). `.venv`는 재생성 필요(D046).
- ffmpeg 9.0.1: winget `Gyan.FFmpeg.Essentials`, `%LOCALAPPDATA%\Microsoft\WinGet\Links\` (2026-10-24 설치).
- PowerShell: `>`는 UTF-16 LE BOM으로 쓴다. 파일은 `[IO.File]::WriteAllText(..., [Text.UTF8Encoding]::new($false))`. 새 경로는 `Join-Path`.
- `_local/`: `mp3gain/`(원본 소스·exe), `test_audio/`(합성 fixture), `compare_gaindb_vs_mp3gain_exe.py`(원본 exe 대조, MSYS2 필요), `LICENSE_REVIEW.md`, `GaindB.zip`.
- 원격: https://github.com/metapbl/GainDB (main만 사용, `genspark_ai_developer`는 삭제 예정 D042).
