# v1.5.0 — scipy 제거 (numpy 블록 IIR) · Release
Status: done (2026-11-25) | 시작: 2026-11-25 (78b6016) | 근거: PRD §2.1 1.5 작업 (D118~D121)

목표: 분석 필터를 numpy만으로 바꿔 exe에서 scipy를 뺀다. 게인·peak·적용 스텝·태그는 1.4.1과 같고, 스트리밍과 통짜 히스토그램은 계속 완전히 같다. v1.5.0을 게시하고 용량을 기록한다.

근거:
- scipy 사용처: `gaindb/analysis.py`의 `lfilter` 네 곳(통짜 `_filter_channel` 2, `TrackAnalyzer.feed` 4회 호출)과 `tests/_gen_fixtures.py`의 `butter`·`sosfilt`
- 시안(Q077): 블록 길이 512, 상태공간(DF2T, scipy zi 규약) 블록 행렬. 필터 0.15→0.34초(240초 한 채널), 차이 2e-10, 합성 곡 54/54 게인 같음. 청크를 블록 경계와 다르게 자르면 4e-9 차이 → 입력 버퍼링으로 없앤다

구조:
- `gaindb/analysis.py` — numpy 블록 IIR(계수별 블록 행렬 캐시), 통짜 경로와 `TrackAnalyzer`가 같은 블록 처리를 쓰도록 필터 입력 자투리 버퍼, scipy import 제거, 동일성 근거 주석 갱신
- `tests/test_iir_numpy.py` (새 파일) — scipy 대조(개발 의존성, 없으면 skip)
- `requirements.txt`, `requirements-dev.txt`(새 파일), `pyproject.toml`, `.github/workflows/ci.yml`, `.github/workflows/macos-gui.yml`, `GainDB.spec` 주석
- `README*.md` 6개, `THIRD_PARTY_LICENSES`, `gaindb/__init__.py`, `docs/release-notes-1.5.0.md`
- `docs/REFERENCE.md` T16 갱신

전역 제약:
- 결과(게인·peak·스텝·태그·CLI 출력)는 바뀌지 않는다. 원본 C 코드를 옮기지 않는다(R§2)
- 테스트는 tempfile 사본. 무손실 판정은 audio_body_sha256
- 코어 변경이므로 작업 2가 끝나면 AVD 동기화 대상임을 알린다 (D012)
- 구조 변경과 동작 변경을 섞지 않는다. 작업마다 커밋 1개, 전체 테스트
- git push·git tag·gh release·build_release.ps1 실행 전 사용자 확인 (D041)

시험 접점: `analysis.analyze_track` / `TrackAnalyzer`(공개 분석 함수)와 scipy `lfilter` 기준값

## 작업
- [x] 1. 실패 테스트 (새 필터 없음으로 2건 실패 확인. n=0은 scipy가 초기화 안 된 zf를 돌려줘 기준에서 빼고 '빈 입력이면 상태 그대로'로 대신) — `tests/test_iir_numpy.py`
  - 9개 샘플레이트 계수 × 합성 신호: 새 필터 출력이 `scipy.signal.lfilter`와 상대 1e-9 이내, 최종 상태(zi)도 같음
  - 청크 분할 7가지(1샘플, 블록 길이±1, 소수 길이 등)로 `TrackAnalyzer`에 먹인 히스토그램이 통짜와 `np.array_equal` (D120)
  - fixture 전체: scipy `lfilter`로 바꿔 끼운 기준과 게인·peak·적용 스텝이 정확히 같음 (D121)
  - scipy가 없으면 scipy 대조만 skip
  - 확인: 새 테스트가 새 필터 함수가 없어 실패
- [x] 2. numpy 블록 IIR로 교체 (282건 OK skip 4, scipy 막고 gaindb·gui import OK. 속도 때문에 yule·butter를 상태공간 하나로 합치고 좌우를 함께 처리, 블록 128샘플·블록 시작 상태는 32블록 그룹 행렬곱(두 단계), 입력은 그룹(4096샘플) 경계로 버퍼링, `_loudness_histogram`은 TrackAnalyzer를 씀) — `gaindb/analysis.py` (after: 1)
  - 확인: 전체 테스트 OK(skip은 mp3gain 대조 4건뿐), `test_streaming_analysis` 그대로 통과, `python -c` 로 scipy를 막고(`sys.modules['scipy']=None`) `gaindb`·`gui` import 성공
- [x] 3. 속도 측정 — 같은 PC, 가장 긴 fixture 사본, 곡 하나 분석(디코드 포함) 3회 중앙값을 78b6016(scipy)과 비교 (after: 2)
  - 확인: 증가 10% 이내, 수치를 이 파일에 기록. 넘으면 멈추고 묻는다
  - 측정 2026-11-25: 가장 긴 fixture(test_gain_48k, 2.5초) 0.154~0.165 → 0.160~0.168초(+2~4%, 기준 통과). 대표성이 없어 240초 합성 곡도 잼: 0.91 → 1.08~1.25초(+19~37%, 기준 초과). 필터 자체는 scipy와 같음(0.29 대 0.30초), 차이는 블록 버퍼·행렬곱과 디코드 경합. 1.4.1 dist 225MB 중 scipy 48MB + scipy.libs 20MB → 사용자 결정 "2 더 최적화" (Q078)
  - 최적화 뒤 2026-11-25 (같은 프로세스에서 1.4.1 분석기와 번갈아 9회씩, 디코드 포함 중앙값): 가장 긴 fixture 0.105~0.106 → 0.102~0.107초(-2.0~+0.2%), 240초 곡 0.83~0.99 → 0.72~0.92초(-6.5~-13.5%). 분석기만 0.39 → 0.36초. 블록·그룹 조합 128·64는 +0~11%, 64·128은 +43%, 96·64는 -9~-11%라 128·32로 정함. 기준 통과
- [x] 4. 의존성 정리 (scipy 없는 새 venv(numpy 2.5.5·PySide6 6.12.0): `import scipy` 실패 확인, `gaindb_cli.py -s s` 출력이 1.4.1(scipy) 코드와 diff 없음(fixture 사본 2개·Album), 전체 282건 OK skip 6(mp3gain 4 + scipy 대조 2). 개발 venv 282건 OK skip 4, pip-audit 취약점 없음) — `requirements.txt`·`pyproject.toml`에서 scipy 삭제, `requirements-dev.txt`(`-r requirements.txt` + scipy), CI 두 워크플로가 dev 파일 설치, spec 주석 (after: 2)
  - 확인: scipy 없는 새 venv에서 `gaindb_cli.py`로 fixture 사본 분석 성공, 전체 테스트(scipy 대조 skip 표시) / `pip-audit -r requirements.txt` 취약점 없음
- [x] 5. 버전·문서 (노트 사용자 승인 2026-11-25) — 1.5.0, README 6개 언어 의존성·감사 문구, THIRD_PARTY_LICENSES SciPy 항목 삭제, REFERENCE T16, 노트 초안(사용자 승인) (after: 4)
  - 확인: `test_readme.py`, readme 표준 §6 검사, 6개 언어 `##` 수 같음, 노트 승인
  - 진행 2026-11-25: README 6개 언어(의존성 목록·기여 절 `pip install -r requirements-dev.txt` 추가·감사·라이선스 문구), THIRD_PARTY_LICENSES SciPy 절 삭제, REFERENCE T16·R§1 갱신, 1.5.0, 노트 초안(용량은 작업 6에서 채움). 6개 언어 `##` 12·배지 4 같음, `pip install -r requirements-dev.txt` 실행 성공(scipy 1.18.1), 금지 정보 없음, 전체 282건 OK skip 4. 노트 승인 2026-11-25
- [x] 6. CI·빌드 — push, CI 3개 OS 초록(mp3gain 대조 포함), `build_release.ps1` BUILD OK, dist에 scipy 폴더 없음, zip·폴더 용량을 1.4.1(96465765 bytes)과 비교해 노트에 기록, 빌드 exe로 fixture 사본 Album 분석·적용·undo (실행 전 확인) (after: 5)
  - 진행 2026-11-25: push 78b6016..8c3cca0, CI run 45547788070 3개 OS 초록 282건(macOS·Ubuntu skip 2 = Windows 전용 subst, mp3gain 1.6.2 대조 4건 ok / Windows skip 4 = mp3gain 없음), 세 러너 모두 requirements-dev.txt로 scipy 1.18.1 설치, scipy 대조 테스트 ok.
  - 빌드 2026-11-25: pip-audit 취약점 없음, BUILD OK, `_internal`에 scipy·scipy.libs·openblas 없음(numpy 2.5.4만), zip 65664786 bytes(1.4.1 96465765, -32%), 폴더 153 MB(du -sm, 1.4.1 225 MB, -32%), zip에 .qm 5개·licenses 있음. 노트 용량 채움
  - Result: 2026-11-25 pass — 사용자 "모두 예"(첫 답은 시험 전 잘못 클릭이라 철회, 파일 무변경으로 확인). 빌드 exe로 사본 3개 Album 분석·적용·undo, exe가 쓴 태그 Track -7.88/-7.41/-7.88·Album -7.87 dB·-5스텝(CLI 기대값과 같음), undo 뒤 audio_body_sha256 세 파일 모두 적용 전과 같음
- [x] 7. Release (CI 3개 OS 초록 run 45550251819 at e0a4488, 빌드 뒤 앱 코드 변경 없음, 태그 v1.5.0 = e0a4488, https://github.com/metapbl/GainDB/releases/tag/v1.5.0, zip 65664786 bytes, latest = v1.5.0, 2026-11-25) — 태그 v1.5.0, GitHub Release (실행 전 확인) (after: 6)
- [x] 8. 인수 (D121 기준 전부 근거 있음, 명세 검토 지적은 1.5.1로 처리) — PRD §1 성공 기준(원본 mp3gain과 같은 dB·태그, undo 비트 동일)과 D121 완료 기준 전부, 명세 검토(대화 맥락 없는 서브에이전트에 이 파일·PRD §2.1 1.5 작업·`git diff 78b6016..`)
  - 확인: 전체 테스트 OK, CI 대조 통과 run 번호 기록
  - 진행 2026-11-25: fixture 사본 13개 전체에서 `-s s -o` 출력(Track dB·스텝·Max Amplitude·global gain·Album)이 1.4.1(78b6016, scipy)과 diff 없음(새 쪽은 scipy 없는 venv), Album 적용(`-a -c`) 뒤 13개 파일 바이트 동일. CI 대조 run 45547788070·45550251819. 속도·용량·exe는 작업 3·6
  - 명세 검토(서브에이전트): 수학·D010 동일성 이상 없음. 지적 — NOTICE:47과 About 창(`gui/dialogs/about_dialog.py:6,91`)에 'NumPy, SciPy'가 남음(1.5.0 zip·exe에 들어감, 번역 문구 아님) / `_iir` docstring의 `zi[:, :10]` 고정 서술 / `_flush` 뒤 `feed`는 지원 안 함(현재 호출처는 무관) / 자체 검토의 '블록 길이 512'가 실제 128·32와 다름 / peak·Album 전체 대조 근거 부족 → 위 13개 대조로 보완. 처리: 사용자 결정 "1 고치고 1.5.1" → 작업 9·10. 자체 검토 512 줄은 고침

## 자체 검토
- 빠진 PRD 기능: 없음 (§2.1 1.5 작업 1·2)
- 테스트로 바꾸지 못한 인수 기준: 속도(작업 3 측정)와 용량(작업 6 측정)은 기록으로, exe 동작은 작업 6 실행으로 확인
- 순서: 2 after 1 · 3, 4 after 2 · 5~8 순서대로
- [AI] 세부: 블록 길이 128·그룹 32(작업 3 측정으로 정함, 시안은 512), 새 테스트 파일 이름, fixture 게인 대조를 scipy 실시간 대조로 함(CI 러너마다 ffmpeg가 달라 fixture 바이트가 달라질 수 있어 고정 기준값 대신)

## 1.5.1 (작업 8 명세 검토 지적, 사용자 결정 "1 고치고 1.5.1" 2026-11-25)
- [x] 9. 남은 SciPy 고지 제거 (NOTICE·About 창·주석·docstring 수정, 배포 대상 NOTICE·THIRD_PARTY_LICENSES·gui·gaindb에 SciPy 고지 없음 — analysis.py 내부 주석 2곳(계수 형식·대체 이력)만 남김, 282건 OK skip 4) — `NOTICE`(NumPy만), `gui/dialogs/about_dialog.py` About 창 서드파티 목록·머리 주석, `gaindb/analysis.py` `_iir` docstring 일반형·`TrackAnalyzer` 사용 설명에 "histogram()/result() 뒤 feed 안 함"
  - 확인: 배포물에 들어가는 파일(NOTICE·THIRD_PARTY_LICENSES·gui·gaindb)에 SciPy 없음(grep), 전체 테스트 OK
- [x] 10. 1.5.1 (CI run 45552950527 at b7f470c 초록, 태그 v1.5.1 = b7f470c, https://github.com/metapbl/GainDB/releases/tag/v1.5.1, zip 65664507 bytes, latest = v1.5.1, 2026-11-25) — 버전·노트(승인)·push·CI 3개 OS·pip-audit·빌드(BUILD OK, zip의 licenses/NOTICE에 SciPy 없음)·exe About 창 확인·태그·Release (실행 전 확인) (after: 9)
  - 진행 2026-11-25: 노트 사용자 승인, push e0a4488..7a01aa4, CI run 45551501955 3개 OS 초록 282건(Windows skip 4, macOS·Ubuntu skip 2). pip-audit 취약점 없음, BUILD OK, zip 65664507 bytes·폴더 153 MB, zip의 licenses/NOTICE는 NumPy만·THIRD_PARTY_LICENSES에 SciPy 없음, scipy 패키지 없음(이름이 비슷한 것은 numpy.libs의 libscipy_openblas64 DLL = numpy 자체 OpenBLAS), .qm 5개.
  - Result: 2026-11-25 pass — 사용자 "눔파이확인했어요"(빌드 exe About 창 서드파티 목록에 NumPy만)
