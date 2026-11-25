# v1.5.0 — scipy 제거 (numpy 블록 IIR) · Release
Status: active | 시작: 2026-11-25 (78b6016) | 근거: PRD §2.1 1.5 작업 (D118~D121)

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
- [ ] 1. 실패 테스트 — `tests/test_iir_numpy.py`
  - 9개 샘플레이트 계수 × 합성 신호: 새 필터 출력이 `scipy.signal.lfilter`와 상대 1e-9 이내, 최종 상태(zi)도 같음
  - 청크 분할 7가지(1샘플, 블록 길이±1, 소수 길이 등)로 `TrackAnalyzer`에 먹인 히스토그램이 통짜와 `np.array_equal` (D120)
  - fixture 전체: scipy `lfilter`로 바꿔 끼운 기준과 게인·peak·적용 스텝이 정확히 같음 (D121)
  - scipy가 없으면 scipy 대조만 skip
  - 확인: 새 테스트가 새 필터 함수가 없어 실패
- [ ] 2. numpy 블록 IIR로 교체 — `gaindb/analysis.py` (after: 1)
  - 확인: 전체 테스트 OK(skip은 mp3gain 대조 4건뿐), `test_streaming_analysis` 그대로 통과, `python -c` 로 scipy를 막고(`sys.modules['scipy']=None`) `gaindb`·`gui` import 성공
- [ ] 3. 속도 측정 — 같은 PC, 가장 긴 fixture 사본, 곡 하나 분석(디코드 포함) 3회 중앙값을 78b6016(scipy)과 비교 (after: 2)
  - 확인: 증가 10% 이내, 수치를 이 파일에 기록. 넘으면 멈추고 묻는다
- [ ] 4. 의존성 정리 — `requirements.txt`·`pyproject.toml`에서 scipy 삭제, `requirements-dev.txt`(`-r requirements.txt` + scipy), CI 두 워크플로가 dev 파일 설치, spec 주석 (after: 2)
  - 확인: scipy 없는 새 venv에서 `gaindb_cli.py`로 fixture 사본 분석 성공, 전체 테스트(scipy 대조 skip 표시) / `pip-audit -r requirements.txt` 취약점 없음
- [ ] 5. 버전·문서 — 1.5.0, README 6개 언어 의존성·감사 문구, THIRD_PARTY_LICENSES SciPy 항목 삭제, REFERENCE T16, 노트 초안(사용자 승인) (after: 4)
  - 확인: `test_readme.py`, readme 표준 §6 검사, 6개 언어 `##` 수 같음, 노트 승인
- [ ] 6. CI·빌드 — push, CI 3개 OS 초록(mp3gain 대조 포함), `build_release.ps1` BUILD OK, dist에 scipy 폴더 없음, zip·폴더 용량을 1.4.1(96465765 bytes)과 비교해 노트에 기록, 빌드 exe로 fixture 사본 Album 분석·적용·undo (실행 전 확인) (after: 5)
- [ ] 7. Release — 태그 v1.5.0, GitHub Release (실행 전 확인) (after: 6)
- [ ] 8. 인수 — PRD §1 성공 기준(원본 mp3gain과 같은 dB·태그, undo 비트 동일)과 D121 완료 기준 전부, 명세 검토(대화 맥락 없는 서브에이전트에 이 파일·PRD §2.1 1.5 작업·`git diff 78b6016..`)
  - 확인: 전체 테스트 OK, CI 대조 통과 run 번호 기록

## 자체 검토
- 빠진 PRD 기능: 없음 (§2.1 1.5 작업 1·2)
- 테스트로 바꾸지 못한 인수 기준: 속도(작업 3 측정)와 용량(작업 6 측정)은 기록으로, exe 동작은 작업 6 실행으로 확인
- 순서: 2 after 1 · 3, 4 after 2 · 5~8 순서대로
- [AI] 세부: 블록 길이 512(시안 값), 새 테스트 파일 이름, fixture 게인 대조를 scipy 실시간 대조로 함(CI 러너마다 ffmpeg가 달라 fixture 바이트가 달라질 수 있어 고정 기준값 대신)
