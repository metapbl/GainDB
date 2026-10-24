# QA_LOG — 질의응답 원장

<!-- 추가만 한다. 고치거나 지우지 않는다. 정정은 새 항목으로 쓰고 이전 Q번호를 적는다. -->
<!-- 전체를 읽지 않는다. 필요한 Q번호나 낱말로 검색한다. -->

## 양식

### Q001 · YYYY-MM-DD · 단계 1 · [U]
Q: 질문
A: 답 (사용자 표현 그대로, 길면 요약하고 "요약" 표시)
→ D001 확정 | OPEN Q005 추가 | 없음

- 출처가 [X]인 항목은 A에 근거 파일과 위치를 적는다. 예: `src/app.py > main`
- 출처가 [AI]인 항목은 A에 "AI 기본값"과 이유를 적고 OPEN의 재확인 칸에 올린다.

---

<!-- 2026-10-24 adopt: 기존 CLAUDE.md(→ docs/legacy/ 예정)·README·코드에서 역추출. 아래 Q001은 양식 예시와 별개. -->

### Q001 · 2026-10-24 · 단계 0 · [X]
Q: 무엇을 하는 프로젝트인가
A: MP3 음량을 재인코딩 없이(무손실) 분석·조정하는 도구. mp3gain과 결과(동작·태그 포맷·출력·수치)를 일치시키는 mp3gain 기반 Python 재구현. 출처: CLAUDE.md > 1, README.ko.md > 첫 문단
→ PRD §1

### Q002 · 2026-10-24 · 단계 0 · [X]
Q: 범위
A: MP3 전용. 무손실 게인은 MP3 프레임 `global_gain` 고유 구조라 타 포맷에 원리적으로 적용 불가. 타 포맷 지원 제안 금지. 출처: CLAUDE.md > 1·3·8.1, README > 범위
→ D001

### Q003 · 2026-10-24 · 단계 0 · [X]
Q: 누가 어떻게 쓰는가
A: AVD로 MP3 지정 다운로드한 음원의 음량을 맞추는 후속 단계 도구이며 단독으로도 동작. 1인 개발자 + AI. GitHub 공개(https://github.com/metapbl/GainDB). 출처: CLAUDE.md > 1
→ PRD §1

### Q004 · 2026-10-24 · 단계 0 · [X]
Q: 최우선 원칙
A: mp3gain 결과 일치. 원본 기능을 임의로 빼거나 단순화하지 않는다. 미루거나 예외를 두려면 사용자 합의 후 기록. 출처: CLAUDE.md > 2.1
→ D002

### Q005 · 2026-10-24 · 단계 0 · [X]
Q: 합의된 예외
A: (1) 디코더: 원본 mpglib 대신 ffmpeg 외부 호출(항구 예외, PATH 호출·미동봉). (2) 샘플레이트: 전 샘플레이트 확장 완료, 저샘플레이트 계수는 공개 표준값 전사. (3) 허용오차 0.1dB. 출처: CLAUDE.md > 2.1, 10.1
→ D003, D004, D005

### Q006 · 2026-10-24 · 단계 0 · [X]
Q: 라이선스와 구현 성격 서술
A: 2026-08 Apache-2.0 → LGPL-2.1-or-later 전환. id3/tag/frame/writer + CLI 분기는 원본 C 개작(파생, 헤더 고지 필수). analysis/decode/api/GUI는 새로 작성. 서술 금지어: clean-room, 파생 영역에 대한 "독립 구현", 파생 부인 문구. 법적 최종 확인은 변호사 검토. 세부는 `_local/LICENSE_REVIEW.md`(로컬 전용, 참조용). 출처: CLAUDE.md > 2.2·2.3, LICENSE, git 3dd1a72
→ D006

### Q007 · 2026-10-24 · 단계 0 · [X]
Q: 기술 스택
A: Python ≥3.13, numpy≥2.0·scipy≥1.13(분석), PySide6≥6.7(GUI), ffmpeg/ffprobe(외부). 프레임 파서·writer는 표준 라이브러리만. venv `.venv`. 출처: pyproject.toml, requirements.txt, CLAUDE.md > 4
→ D023

### Q008 · 2026-10-24 · 단계 0 · [X]
Q: 장기 비전과 AVD 연계
A: GaindB가 정본, AVD는 `gaindb/` 코어를 소비. 수정은 GaindB 먼저. 다운로드 후 별도 단계로 api 호출. 소비 방식(vendoring vs pip)은 연계 착수 시 결정. 당면 목표는 공개 후 유지·마무리. 출처: CLAUDE.md > 1, 10.1
→ D012

### Q009 · 2026-10-24 · 단계 0 · [X]
Q: 현재 진행 상태
A: 1~8단계(파서·분석·디코드·태그·CLI·샘플레이트·라이선스 검토·GUI) 완료. 공개 후 유지 단계. 버전 0.5.1(`gaindb/__init__.py`). 테스트 139건(`def test_` 실측 139). 출처: CLAUDE.md > 10.2·10.3, git 4b9abb4
→ PROGRESS 후보

### Q010 · 2026-10-24 · 단계 0 · [X]
Q: 남은 할 일
A: (1) 변호사 최종 검토 → 그 뒤 정식 GitHub Release 발행. (2) 오디오 경로 변경 시 실클릭 회귀(취소 후 audio_body_sha256 확인) 체크리스트. 출처: CLAUDE.md > 10.4
→ D021, PROGRESS 후보

### Q011 · 2026-10-24 · 단계 0 · [X]
Q: 보류 항목
A: 사용자가 요구하기 전에는 제안하지 않음: 255 클램프 사전 경고(보류 확정), steps==0 태그 재확인 최적화, Constant Gain GUI, Max No-clip GUI, scipy 제거(용량 215→145MB). 출처: CLAUDE.md > 10.5
→ D022, PRD §2.3

### Q012 · 2026-10-24 · 단계 0 · [X]
Q: 검증 방법
A: `python -m unittest discover -s tests`, 외부 의존 없는 unittest. fixture는 `tests/_gen_fixtures.py`가 고정 시드로 `_local/test_audio/`에 생성(ffmpeg 필요). 테스트는 tempfile 사본만 사용(FixtureGuard), 무손실 판정은 audio_body_sha256. 원본 exe 대조는 `_local/` 수동 스크립트. 출처: CLAUDE.md > 10.1 검증 인프라, 9
→ D019, PRD §6

### Q013 · 2026-10-24 · 단계 0 · [X]
Q: 프로젝트 고유 작업 규칙
A: 커밋 신원 metapbl / ggoyong2@gmail.com 고정(현재 설정 일치 확인). Conventional Commits, 의미 단위마다 커밋. PowerShell 파일 쓰기는 BOM 없는 UTF-8. 출처: CLAUDE.md > 1·7
→ CLAUDE.md 후보

### Q014 · 2026-10-24 · 단계 0 · [X]
Q: 원본 참고 자료 취급
A: 원본 C·VB 소스는 `_local/mp3gain/`에 보관, git·배포물 제외. 원본 exe는 실행 결과만 검증 기준. GUI는 원본 화면 관찰만, 코드 미이전. 출처: CLAUDE.md > 5
→ REFERENCE 후보

### Q015 · 2026-10-24 · 단계 0 · [X] · 문서↔실제 차이
Q: 로컬 경로
A: 문서는 `C:\Users\ggoyo_zhxlvdr\GaindB`, 실제는 `C:\Users\Administrator\My Projects\GaindB`. 실제를 사실로 봄. 출처: CLAUDE.md > 1·4
→ 새 문서에는 경로를 적지 않음 [AI]

### Q016 · 2026-10-24 · 단계 0 · [X] · 문서↔코드 차이
Q: "독립 구현" 서술
A: 서술 원칙(2.2)은 파생 영역에 "독립 구현" 사용 금지. 그런데 README.md:7 "independent re-implementation", README.ko.md:8 "독립 재구현", `gui/dialogs/about_dialog.py`:3 docstring "independent implementation", CLAUDE.md 4 트리 "gui/ (독립 구현)"·8.1 "독립 구현/독립 재작성"이 남아 있음. about_dialog는 새로 작성 영역이라 문제 없을 수 있으나 README 두 곳은 프로젝트 전체를 지칭. 코드 수정은 adopt 범위 밖.
→ OPEN 후보 (README 문구 정리 여부)

### Q017 · 2026-10-24 · 단계 0 · [X] · 문서 내부 모순
Q: About 다이얼로그 라이선스 서술
A: CLAUDE.md 10.2는 "Apache-2.0" 고지라 적었으나 10.3과 코드(about_dialog.py에 Apache 없음)는 LGPL로 갱신됨. 코드를 사실로 봄.
→ 없음 (새 문서에 반영)

### Q018 · 2026-10-24 · 단계 0 · [X] · 문서 내부 모순
Q: exe 라이선스 동봉 자동화
A: 10.4는 "미착수(조건부)", 10.2·10.4 다음 항목은 "구현 완료". `build_release.ps1`·`GainDB.spec`·`licenses/qt/` 존재, git 2bcbdb3. 완료로 봄.
→ 없음

### Q019 · 2026-10-24 · 단계 0 · [X] · 문서↔코드 차이
Q: 버전
A: CLAUDE.md는 0.5.0 승격까지 기록, 코드·pyproject는 0.5.1(git 4b9abb4). 코드를 사실로 봄.
→ 없음

### Q020 · 2026-10-24 · 단계 0 · [X] · 환경 차이
Q: 협업 환경 전제
A: CLAUDE.md 5·6·8.3~8.6은 채팅형 협업 전제(Claude가 디스크를 못 읽어 사용자가 붙여넣기, here-string 명령으로 파일 반영). Claude Code는 파일을 직접 읽고 쓰므로 해당 규칙은 버림 후보. 단 `_local/mp3gain/`도 이제 직접 읽을 수 있음.
→ 버림 목록

### Q021 · 2026-10-24 · 단계 0 · [X] · 환경
Q: 이 PC의 테스트 실행 조건
A: `ffmpeg`가 현재 PATH에서 찾아지지 않음(Get-Command 결과 없음). `_local/test_audio/`는 있음. 테스트 실행 전 확인 필요.
→ OPEN 후보

### Q022 · 2026-10-24 · 단계 0 · [U]
Q: 로컬 전용 자료 처리
A: GaindB.zip은 커밋 불필요한 로컬 전용 자료 → `_local/`로 이동(완료). `_local/LICENSE_REVIEW.md`는 로컬 전용 참조 자료로 두고 이관 대상에서 제외.
→ D025

### Q023 · 2026-10-24 · 단계 0 · [U] · 정정 Q010
Q: 변호사 최종 검토
A: "변호사검토는 끝났으므로 불필요합니다."
→ D021 대체 → D026

### Q024 · 2026-10-24 · 단계 0 · [U] · 정정 Q006
Q: 프로젝트 라이선스
A: "프로젝트 기본 라이선스는 mit라이선스로 변경하고 고지해야할 라이선스는 현행을 유지" 희망. 확인 사실 [X]: 원본 저작권 헤더(Glen Sawyer 외 / Robinson·Sawyer)가 있는 파일은 frame.py·id3.py·tag.py·writer.py·analysis.py·gaindb_cli.py 6개. 이 파일들은 LGPL 원본의 개작이라 MIT로 바꿀 수 없음.
→ OPEN: 라이선스 구성 방식 (혼합 / 전체 LGPL 유지)

### Q025 · 2026-10-24 · 단계 0 · [U] · 정정 Q016
Q: 구현 성격 서술
A: "mp3gain의 오픈소스 코드를 이용해서 독립재구현한 것이 아니라 오픈소스코드를 읽고 리팩토링한 것임을 인정하겠습니다."
→ D006 서술 갱신. README "독립 재구현" 문구는 정리 대상(코드 단계에서)

### Q026 · 2026-10-24 · 단계 0 · [U]
Q: ffmpeg 배포 방식
A: "ffmpeg는 동봉하지 않고 ffmpeg의 기본 설치 path를 이용할생각입니다." 확인 사실 [X]: 현재 decode.py는 PATH의 "ffmpeg"/"ffprobe"만 호출. 이 PC는 PATH와 흔한 설치 위치(winget·C:\ffmpeg·Program Files·scoop·choco) 어디에도 ffmpeg 없음.
→ OPEN: "기본 설치 path"의 뜻 (PATH만 / 알려진 설치 위치도 탐색)
### Q027 · 2026-10-24 · 단계 0 · [U] · Q024 해결
Q: 라이선스 구성 (혼합 / 전체 LGPL 유지 / 재작성 후 MIT)
A: "lgpl유지해서 현행방식으로 계속하겠습니다."
→ D006 유지

### Q028 · 2026-10-24 · 단계 0 · [U] · Q026 해결
Q: ffmpeg 탐색 범위 (PATH 우선 + 알려진 설치 위치 / PATH만)
A: "추천대로" → PATH 우선, 없으면 알려진 설치 위치(winget, C:\ffmpeg\bin, Program Files, macOS /opt/homebrew/bin·/usr/local/bin) 탐색. 동봉 안 함.
→ D003 대체 → D028. decode.py 변경 필요(계획 단계 작업 후보)
### Q029 · 2026-10-24 · 단계 1 · [U] · OPEN O01
Q: 성공 기준 (관찰 장면 하나)
A: 추천안에 "동의합니다": 폴더의 MP3를 GUI에서 Album 분석·적용 → 원본 mp3gain과 같은 dB·태그, undo 하면 오디오 비트 동일 복원.
→ D029

### Q030 · 2026-10-24 · 단계 5 · [U] · OPEN 재확인(브랜치)
Q: 브랜치 정책
A: "브랜치는 main 하나로만 하겠습니다."
→ D030. 원격 genspark_ai_developer 브랜치 처리는 별도 확인(OPEN O11)
### Q031 · 2026-10-24 · 단계 2 · [U] · OPEN O02
Q: 정식 GitHub Release 발행을 이번 범위에 넣는가
A: "네"
→ D031

### Q032 · 2026-10-24 · 단계 2 · [U] · OPEN O03
Q: AVD 연계를 이번 범위에 넣는가
A: "avd는 다른 세션에서 진행예정"
→ D032

### Q033 · 2026-10-24 · 단계 2 · [U] · OPEN O04
Q: README "독립 재구현"·about_dialog docstring 문구 정리를 이번에 하는가 (계획 첫 작업)
A: "네 좋습니다."
→ D033

### Q034 · 2026-10-24 · 단계 2 · [U] · OPEN O05
Q: "있으면 좋음" 항목
A: "좋습니다." (추천안: 없음, 보류 목록이 그 역할)
→ D034

### Q035 · 2026-10-24 · 단계 3 · [U] · OPEN O06
Q: 인수 기준을 기존 테스트 139건에서 기능별로 뽑아 초안으로 보여도 되는가 (ffmpeg 탐색은 새로 작성)
A: "네 동의합니다 진행하십시오"
→ D035

### Q036 · 2026-10-24 · 단계 3 · [U] · OPEN O07
Q: ffmpeg를 끝내 못 찾을 때 GUI 동작 (대화상자 + README 설치 안내 링크 / 상태바 문구만). CLI는 영문 오류 + 찾아본 위치 표시
A: "네 동의합니다" → 추천안(대화상자 + 설치 안내 링크), CLI 기본값 수용
→ D036
### Q037 · 2026-10-24 · 단계 3 · [U] · 되짚기 + OPEN O12
Q: 단계 3 되짚기 확인, macOS 실기기 확인 가능 여부
A: "네 확인이 어렵습니다." → 되짚기 맞음(해석), macOS 실기기 확인 불가. 추가 질문: "macos는 그대가 검증할수 있는지 궁금합니다"
→ D036 확정, D037. OPEN O13 (macOS CI 여부)
### Q038 · 2026-10-24 · 단계 3 · [U] · OPEN O13 + D029 확인 방법
Q: macOS 검증 방식, 성공 기준 확인 주체
A: "mp3gain도 cli방식 프로그램이 공개되어있으니까 그대가 검증할 수 있다고 봅니다. 나머지는 동의합니다" → macOS CI 채택, 성공 기준의 mp3gain 대조를 AI가 수행.
확인 사실 [X]: `_local/mp3gain/src/mp3gain.exe`와 `_local/compare_gaindb_vs_mp3gain_exe.py`(9개 저샘플레이트 fixture, scan만 대조) 있음. exe는 MSYS2 UCRT64 DLL이 필요한데 이 PC에 C:\msys64 없음 → 실행 실패(exit 53). ffmpeg도 없음.
→ D038, D039
### Q039 · 2026-10-24 · 단계 3 · [U] · 되짚기(검증 방식)
Q: 성공 기준 대조 항목, GUI offscreen 대조, 3 OS CI 확인
A: "모두 맞고 동의합니다 진행하십시오"
→ D038 확정. 단계 4: 기술 결정은 adopt에서 확정됨, CI만 PRD §4에 추가
### Q040 · 2026-10-24 · 단계 5 · [U] · OPEN O08~O11
Q: ffmpeg 설치 / 편집 시 자동 검사 / 위험 명령 / 원격 genspark 브랜치 삭제
A: "네 추천대로 진행하겠습니다" + "ffmpeg는 그대가 제 로컬에 설치할수없나요? 제가 데스크탑앞에 있지 않고 외부에 위치한 상태입니다."
→ D040 (check 훅 = py_compile), D041 (확인 대상 명령), D042 (genspark 브랜치 삭제, 구현 단계에서 확인 후). ffmpeg는 AI가 winget으로 설치(사용자 승인 대기)
### Q041 · 2026-10-24 · 단계 5 · [X] · ffmpeg 설치 결과
Q: ffmpeg 설치와 테스트 실행
A: 사용자 승인("네 윈겟설치 좋습니다 진행하세요") 후 winget으로 Gyan.FFmpeg.Essentials 9.0.1 사용자 범위 설치 완료. `ffmpeg -version` 확인, 경로 `%LOCALAPPDATA%\Microsoft\WinGet\Links\`. 테스트는 실행 못 함: `.venv`가 옛 PC에서 만든 것(home=C:\Python314, 없음)이라 깨짐. 이 PC에는 Python 3.15(py launcher)만 있고 numpy·scipy·PySide6 미설치. venv 재생성은 의존성 설치라 PRD 승인 전 금지(철칙 1).
→ OPEN O14 (venv 재생성 시점)
### Q042 · 2026-10-24 · 단계 5 · [AI] · PRD 검사 (discover §5)
Q: 맥락 없는 검사자가 PRD만 읽고 낸 지적 처리
A: 요약. 지적 25여 건 중 대부분은 AI 기본값으로 PRD에 채움(되짚기에서 확인): "같다"의 정의, 이번 작업 순서·완료 기준(서술 정리·CI·Release), F6 후보 폴더 OS별 목록·순서·같은 출처 규칙·Linux는 PATH만·실패 처리·ffmpeg 불필요 작업은 안 막음·찾기 함수 추가(인터페이스 문장 모순 해소)·링크 대상·GWT 6개, §5 PATH 문장 모순 해소, CI 실행 조건·OS·Python 3.13·fixture 생성·mp3gain 설치·실패 처리. 버림: draft 상태 지적(관문 자체), 성능 한계값(기존 동작, 이번 범위 아님). 사용자에게 물을 것: Release 버전, macOS 배포물.
→ OPEN O15, O16
### Q043 · 2026-10-25 · 단계 5 · [U] · 되짚기(PRD 검사 보완) + OPEN O14·O15·O16
Q: 검사 보완 기본값 9개 확인, Release 버전, macOS 배포물, venv 재생성 시점
A: "추천대로" → 기본값 9개 맞음(해석), 버전 0.6.0, macOS 배포물 없음(소스 실행), venv는 PRD 승인 직후 계획 0번 작업
→ D043, D044, D045, D046
### Q044 · 2026-10-25 · 단계 5 · [U] · PRD 승인 관문
Q: PRD를 승인하는가
A: "네 승인합니다"
→ PRD 상태 approved (2026-10-25)
### Q045 · 2026-10-25 · 단계 6 · [U] · 문서 관문
Q: 문서 구성(CLAUDE.md·PROGRESS·REFERENCE·settings·훅)을 승인하는가. git 추적 범위는 추천안(모두 추적, settings.local.json만 제외)으로 둠
A: "승인합니다"
→ CLAUDE.md 첫 줄 <!-- metarche -->, D047