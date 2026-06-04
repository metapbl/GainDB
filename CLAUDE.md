# Gain dB — Claude 컨텍스트 파일

> 새 세션 시작 시 Claude 에게 프로젝트 맥락을 즉시 제공하는 컨텍스트 파일.
> 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고, 그 세션 단계에 필요한 C 소스를 함께 붙여넣는다 (자세한 방법은 "12. 새 세션 시작 방법" 참조).

---

## 1. 프로젝트 정체성

- **표시 이름**: Gain dB
- **기술 이름(폴더·저장소·패키지)**: `GaindB`
- **성격**: MP3 파일의 음량을 **무손실(재인코딩 없이)** 로 분석·조정하는 도구. 원본 MP3Gain 의 기능·동작·태그 포맷·출력을 Python 으로 **빠짐없이 동일하게 재현**하는 것을 목표로 한다. 단, 원본 C 코드를 옮기는 "포팅"이 아니라 공개 사양·관찰된 동작만 보고 독립 구현하는 **clean-room 재구현**이다(상세는 4 참조).
- **범위**: **MP3 단독 전용**. AAC/FLAC/Opus 등 타 포맷은 다루지 않는다(원본 mp3gain 본체도 MP3 전용이며 AAC 는 별도 빌드. 사유는 5·10 참조).
- **위치**: AVD(AV_Downloader)로 "MP3 지정" 다운로드한 음원의 음량을 고르게 맞추는 **후속 단계 도구**. 단독으로도 동작.
- **로컬 경로**: `C:\Users\ggoyo_zhxlvdr\GaindB`
- **라이선스 방침**: 4 참조 (clean-room 우선, 개인 로컬 사용).

## 1.1. 원본 동일 재현 원칙 (최우선 원칙)

- 원본 mp3gain 의 **기능·동작·태그 포맷·출력·옵션을 빠짐없이 그대로 재현**한다. 임의로 기능을 빼거나 단순화하지 않는다.
- 불가피하게 일부를 미루거나 예외를 두어야 할 때는 **Claude 가 임의로 정하지 않는다.** 반드시 사용자와 합의하고, 그 결정을 12.1 진척 로그에 "축소가 아니라 합의된 예외 / 진행 중 미완"임이 드러나게 명시한다.
- "동일 재현"은 **결과(동작·태그 포맷·출력·수치)의 일치**를 뜻한다. 그 구현은 원본 C 코드를 옮기지 않고 공개 사양·관찰된 동작으로 독립 작성한다 — 즉 동일 재현과 clean-room(4)은 모순되지 않는다(결과는 일치, 코드는 독립).
- 아래는 사용자와 **이미 합의된 예외/우선 구현**이다. 이는 기능 축소가 아니다.
  - **디코더(항구적 예외)**: PCM 추출은 원본의 `mpglibDBL` 디코더를 포팅하지 않고 외부 도구(ffmpeg)를 호출한다. LGPL 분리·실용성 때문이며, 구현 수단만 다를 뿐 **분석 결과(라우드니스 dB)는 원본과 일치**시킨다(7 참조).
  - **샘플레이트(우선 구현·확장 대상)**: 실제 음원의 절대다수가 44.1k·48k 이므로 이 둘을 먼저 구현·검증했다. 원본은 ReplayGain 사양의 모든 샘플레이트 계수를 지원하므로, 나머지 샘플레이트도 원칙상 추가 대상이다(축소가 아니라 미완. 상세는 12.1).

## 2. 프로젝트 구조

루트: `C:\Users\ggoyo_zhxlvdr\GaindB`

```
GaindB/
├─ gaindb/                 # 패키지
│  ├─ __init__.py
│  ├─ frame.py             # [1단계] 프레임 파서: _BitReader, 헤더 파싱, global_gain 읽기
│  ├─ writer.py            # [1단계] global_gain ±N 무손실 적용 + CRC 재계산
│  ├─ decode.py            # [2/3단계] ffmpeg/ffprobe 로 MP3→PCM
│  ├─ id3.py              # [5단계 ⑤] ID3v2 태그(RVA2 + TXXX) 읽기/쓰기
│  └─ analysis.py          # [2단계] ReplayGain 분석(Track/Album), dB→스텝 변환
├─ scan_gain.py            # [1단계·개발용 검증 CLI] global_gain 스캔·출력 (5단계 통합 CLI 로 흡수 예정)
├─ apply_gain.py           # [1·2단계] CLI: 수동/auto/album 게인 적용
├─ inspect_tag.py          # [4단계·개발용 검증 CLI] 태그 상태 덤프 (5단계 통합 CLI 로 흡수 예정)
├─ mp3gain/                # 원본 C 소스(LGPL, 사양 참고용). git 제외
│  ├─ LICENSE  Makefile  README.md
│  └─ src/
│     ├─ mp3gain.c / .h        # [참고 완료] 프레임 파싱 + global_gain 적용 + 메인 흐름
│     ├─ gain_analysis.c / .h  # [참고 완료] ReplayGain 필터 계수·RMS·통계
│     ├─ apetag.c / .h         # [4단계] APEv2 태그(전 필드 + undo)
│     ├─ id3tag.c / .h         # [4단계] ID3v2 태그(RVA2 + TXXX)
│     ├─ rg_error.c / .h       # 오류 처리(보조)
│     └─ (replaygaindll.*, *.dsp/.dsw/.sln/.vcproj/.rc, resource.h, Makefile — 빌드·래퍼, 무시)
├─ CLAUDE.md               # 이 컨텍스트 파일
├─ CopyClaudeMd.bat        # CLAUDE.md 사본 동기화 스크립트
├─ .gitignore
├─ 10cm - 사랑은 은하수 다방에서.mp3   # 테스트 음원(git 제외, 48k)
└─ Debussy - Arabesque No.1.mp3       # 테스트 음원(git 제외, 44.1k)
```

(구조가 바뀌면 이 트리와 12.1 진척 로그를 함께 갱신한다.)

## 3. 협업 모델

- **작업 방식**: 1인 개발자 + AI 페어 프로그래밍.
- **성격**: 원본 mp3gain 의 기능을 완전히 재현하면 완성되는 유틸리티. 한 번 완성해 원본과 동등하게 동작하면 종료.
- **버전관리**: 로컬 Git (원격 저장소 없음 기본, 단계별 커밋으로 안전망 확보). 공개는 최후의 선택지.
- **이 파일 관리**: 컨텍스트 파일은 짧게 유지한다. 단계 완료 시 12.1 진척 로그만 갱신하고, 끝난 단계의 세부 구현 설명은 한두 줄 요약으로 압축한다. 새 항목 추가 시 기존 항목과 중복·비대화되지 않게 한다. **단, 1.1 원본 동일 재현 원칙을 약화시키는 방향으로는 압축·수정하지 않는다.**

## 4. 라이선스 방침

- 원본 MP3Gain 은 C 로 작성된 **LGPL v2.1** 오픈소스(2009년경 개발 중단).
- **clean-room 방식 우선**: 원본 C 코드를 직접 번역(복붙)하지 않고, 공개된 사양(ReplayGain 알고리즘, MPEG 오디오 프레임 구조, 태그 포맷)과 관찰된 동작만 보고 독립 구현한다. 알고리즘·파일 포맷·태그 포맷은 저작권 대상이 아니므로 LGPL 구속을 피할 수 있음.
- 원본 코드를 그대로 번역하면 결과물에 LGPL 이 따라옴. 다른 언어로 옮겨도 2차적 저작물로 간주됨. 그러므로 **결과(동작·포맷·출력)는 원본과 일치시키되, 코드는 독립 작성**한다(1.1 참조).
- 개인 로컬 사용 중에는 "배포"가 없으므로 LGPL 의무는 사실상 발생하지 않음. 원본 C 소스(`mp3gain/`)를 git 에서 제외하는 것도 이 분리를 위함. 배포 계획이 생기면 그때 변호사 검토 필요 (Claude 는 변호사가 아님).

## 5. 핵심 기술 원리

- **무손실 음량 조정**: MP3 각 프레임의 사이드 정보 안 `global_gain`(8bit) 필드를 직접 ±N 하여 음량 조절. 디코더는 `2^(gain/4)` 로 샘플을 곱하므로 1스텝 ≈ 1.5dB. 재인코딩 없음 → 무손실. **MP3 고유 구조라 타 포맷에 적용 불가**(범위를 MP3 전용으로 못박는 근거).
- **음량 분석**: PCM 으로 디코딩 후 David Robinson 의 ReplayGain 알고리즘(equal-loudness 필터 + RMS + 통계, 95퍼센타일 부근)으로 인지 음량 계산. 목표값(기본 89dB)에 맞추는 데 필요한 게인 스텝 수를 산출.
- **Track gain / Album gain** 두 모드. Album 은 곡별 히스토그램을 누적해 단일 dB 산출 후 전 곡에 동일 스텝 적용.
- **태그(원본 전 기능 재현 대상)**: 원본은 APEv2(기본) 또는 ID3v2(`-s i`) 태그에 다음을 기록·읽기·갱신·제거한다 — ReplayGain 표준 필드(`REPLAYGAIN_TRACK_GAIN`/`_PEAK`, `REPLAYGAIN_ALBUM_GAIN`/`_PEAK`, ID3 는 추가로 RVA2 프레임·`replaygain_reference_loudness`), mp3gain 고유 필드(`MP3GAIN_MINMAX`, `MP3GAIN_ALBUM_MINMAX`, `MP3GAIN_UNDO`). 게인 적용 시 이 값들을 일관되게 갱신한다(undo 누적, gain 에서 dB 차감, peak 에 2^(N/4) 곱, minmax 에 N 가감 — 원본 `changeGainAndTag` 동작). undo 는 이 누적된 역방향 값으로 원복한다.

## 6. 원본 참고 자료

- 소스 미러: https://github.com/Sound-Linux-More/mp3gain · 원조: https://sourceforge.net/projects/mp3gain/
- **원본 C 소스는 로컬 `mp3gain/src/` 에 보관**(master.zip 압축 해제본, 2 트리 참조). LGPL 분리를 위해 git 제외. Claude 는 이 폴더를 직접 읽지 못하므로, Claude 가 필요한 함수/구간을 지목하면 사용자가 해당 파일에서 찾아 붙여넣어 제공한다.
- 단계별 대상 파일은 2 트리의 `[N단계]` 표시 참조.

## 7. 기술 스택

- **언어**: Python 3 (3.13/3.14 등). 1단계는 순수 표준 라이브러리(외부 의존성 없음).
- **신호처리**: numpy + scipy (2단계 필터·RMS·통계).
- **MP3 디코딩(PCM 추출)**: 외부 도구(ffmpeg 직접 호출) 사용 — 원본의 `mpglibDBL` 디코더는 옮기지 않는다. 이는 사용자와 합의된 항구적 예외이며(1.1 참조), 구현 수단만 다를 뿐 분석 결과 dB 는 원본과 일치시킨다. ffmpeg 는 PATH 호출(GPL 동봉 안 함, 개인 로컬).
- **가상환경**: venv (`.venv`).

## 8. 구현 단계

> 아래 단계는 작업을 나누기 위한 구획일 뿐이며, **어느 단계도 원본 기능을 축소·생략하지 않는다**(1.1). 분량 추정은 참고용이다.

1. **[완료] MP3 프레임 파서 + `global_gain` 읽기/쓰기** — 순수 Python. 읽기·쓰기·무손실 round-trip 검증 끝(상세는 12.1).
2. **[완료] ReplayGain 분석기** (numpy/scipy) — equal-loudness 필터 + RMS + 통계, Track/Album gain, dB→스텝 변환. 44.1k·48k 검증 완료(나머지 샘플레이트는 확장 대상, 1.1·12.1).
3. **[완료] MP3 디코딩(PCM 추출)**: ffmpeg/ffprobe subprocess. 2단계 입력 공급(`gaindb/decode.py`).
4. **[완료] 태그 처리** — APEv2 읽기·쓰기·갱신·제거, scanFrameGain(min/max), changeGainAndTag 동등, undo, auto/album 태그 연결까지 완료. otherFields·Lyrics3/ID3v1 꼬리 보존. ID3v2(RVA2/TXXX)는 ⑤로 분리(아래 12.1). 검증 완료.
5. **[진행 예정] CLI / 옵션 / 일괄 처리** — 원본 옵션을 빠짐없이 재현(`-r`/`-a`/`-e`/`-g`/`-l`/`-d`/`-m`/`-k`/`-c`/`-w`/`-s c|d|s|r|i|a`/`-u`/`-o`/`-q`/`-p`/`-x`/`-f`/`-t`/`-T` 등), 클리핑 경고·자동 클립(`-k`), database 출력(`-o`) 포함.

## 9. 개발 환경 · 작업 흐름

- **OS**: Windows. 셸은 VS Code 통합 터미널(PowerShell). cwd=워크스페이스 루트 가정, `cd` 는 필요할 때만.
- **에디터**: VS Code.
- **커밋**: 의미 단위가 끝날 때마다 즉시 커밋. Conventional Commits (`feat:`/`fix:`/`chore:`/`docs:`/`refactor:`).
- **PowerShell 함정**: `>` 리다이렉션은 UTF-16 LE BOM 으로 씀. 대안 `... | Out-File -Encoding utf8 <파일>`.

## 10. Claude 응답 규칙

### 10.1. 범위 고수 (포맷)

MP3 전용이다. 타 포맷 지원 제안은 하지 않는다. 무손실 게인 조정은 MP3 `global_gain` 필드 기법이라 타 포맷에 원리적으로 적용 불가. (이는 포맷 범위 규정일 뿐, 원본 기능 축소가 아니다 — 원본 mp3gain 본체도 MP3 전용.)

### 10.2. 원본 동일 재현 + clean-room 준수

- 원본 기능을 **임의로 빼거나 단순화하지 않는다**(1.1). 무언가를 미루거나 예외로 두려면 먼저 사용자와 합의하고 12.1 에 명시한다.
- 사용자가 제공한 원본 C 소스는 **사양·동작 이해 목적으로만** 읽고, 코드를 그대로 옮기지 않는다. 알고리즘·비트 레이아웃·필터 계수·태그 포맷 같은 공개 사양만 차용해 Python 으로 독립 재작성한다.

### 10.3. 코드 제시 단위

- 변경이 **함수 2개 이하**에서만 일어나고 모듈 최상위를 안 건드리면 → 변경된 함수를 **개별 코드 블록으로 함수 단위 발췌**.
- 그 외(함수 3개 이상·최상위 변경·새 함수·시그니처 변경) → **파일 전체**.
- 어느 경우든 코드 블록 바깥에 변경 지점을 한 문장으로 명시.

### 10.4. 코드 제시 전 확인

코드 블록을 보내기 전 "코드를 보내드릴까요?" 라고 한 박자 묻고, 동의 후 다음 응답에서 제시한다. 설계·진단·합의가 코드보다 앞에 온다.

### 10.5. 터미널 명령 동봉

파일을 수정·추가·삭제하는 코드를 제시할 때는 디스크 반영·커밋 명령을 같은 응답에 함께 제시. 기본 흐름 ① `git add <파일>` ② `git status` ③ `git commit -m "..."`. (원격 저장소 없으므로 `git push` 생략.) 환경은 PowerShell, cwd=루트. 신규 파일·디렉터리는 `New-Item -ItemType {Directory|File} -Force` 로 만든 뒤 본문은 VS Code 에 붙여 넣음 — `-Force` 는 기존 파일을 빈 파일로 덮으므로 한 줄 경고.

### 10.6. 마크다운 파일 전송

마크다운 파일 본문에 코드 펜스가 있으면 바깥 펜스는 안쪽보다 백틱을 하나 더 쓴다(안쪽 3개 → 바깥 4개).

### 10.7. 서식

- 불릿은 `-` + 공백 1칸, 하위 불릿은 부모 기준 2칸 들여쓰기.
- `##`/`###` 헤더에 1, 1.1 형식 번호(깊이 2까지).
- 과한 볼드·리스트 남용 지양, 산문 우선.

## 11. 알려진 함정 (영구 제약)

- **`global_gain` 위치 계산이 1단계의 핵심 난점이었음**: 사이드 정보 안의 비트 오프셋을 MPEG 버전·채널 모드별로 정확히 짚어야 함. (1단계에서 해결·검증 완료.)
- **분석에는 디코딩 필요, 적용엔 불필요**: 음량 *적용*은 프레임 게인 필드만 건드림(디코딩 불필요). 음량 *분석*만 PCM 디코딩 필요. 두 경로 혼동 금지.
- **0-gain 프레임은 ±N 으로 안 바뀜**: `gain==0` 이면 그대로 둠(원본 동작). round-trip 완전복원은 0-gain 프레임이 없는 파일에서만 보장.
- **타 포맷 적용 불가**(10.1) / **원본 코드 직접 번역 금지**(4·10.2) / **원본 기능 임의 축소 금지**(1.1·10.2).
- **이 미러의 `.c` 는 크롤 불가**: `application/octet-stream` MIME. 그래서 C 소스는 로컬 보관 + 사용자가 붙여넣어 제공(6 참조). Claude 가 크롤로 가져오려 시도하지 말 것.

## 12. 새 세션 시작 방법

새 세션 첫 메시지에 본 파일(CLAUDE.md)을 첨부하고 "먼저 읽어달라"는 한 줄을 덧붙인다. (`CopyClaudeMd.bat` 실행 → 채팅 입력창에 Ctrl+V 로 파일 첨부.) 이어 그 세션 단계에 필요한 C 소스(.c/.h)를 붙여넣어 제공한다. 검색 도구는 최신 정보 확인용으로만 쓰고, 원본 소스 입수에는 쓰지 않는다.

### 12.1. 진척 로그 / 다음 세션 시작점

**1단계 완료** (프레임 파서 + `global_gain` 읽기/쓰기). 결과물: `gaindb/frame.py`(읽기 파서), `gaindb/writer.py`(±N 무손실 적용 + CRC 재계산), `scan_gain.py`/`apply_gain.py`(CLI). Debussy 파일로 round-trip 바이트 동일 검증 완료.

**2단계 완료** (ReplayGain 분석기 + 디코딩 + dB→스텝 + Track/Album). 결과물:

- `gaindb/decode.py` — ffmpeg/ffprobe subprocess 로 MP3→PCM. (left, right, sample_rate) 반환, 원본 사양 스케일(±32768)로 정규화. ffmpeg 는 PATH 호출.
- `gaindb/analysis.py` — ReplayGain. 필터 계수는 공식 사양(Hydrogenaudio "Original ReplayGain specification" Tables 1·2)에서 옮김(clean-room). yulewalk→Butterworth 캐스케이드(scipy.signal.lfilter) → 50ms RMS → 0.01dB 히스토그램 → 95퍼센타일 → PINK_REF(64.82) 차감. `track_histogram`(곡별 히스토그램)·`gain_from_histograms`(누적 합산 후 단일 dB)·`db_to_steps`(원본 round-half-away-from-zero, 제수 5*log10(2)).
- `apply_gain.py` — `apply_track_gain`, `apply_album_gain`(decode→히스토그램만 보관·PCM 해제→누적→단일 스텝→전 곡 동일 적용), CLI 수동/`auto`/`album` 모드(main 은 모드 우선 판별).
- 검증: Track 은 3곡에서 ffmpeg `replaygain` 필터와 0.02 dB 이내 일치(-0.79/-0.77, -3.60/-3.58, -6.05/-6.03). Album 은 44.1k+48k 혼합에서 -5.05 dB → -3 스텝(개별 -0.79/-6.05 사이·산술평균 아님) 확인. 혼합 샘플레이트 누적 정상.
- **샘플레이트**: 현재 44.1k·48k 구현·검증 완료. 원본은 ReplayGain 사양 전 샘플레이트를 지원하므로 나머지도 추가 대상(1.1 — 축소가 아니라 미완. 실제 음원 절대다수가 44.1k/48k 라 우선 구현에 사용자 합의).
- 미해결 관찰: 48k 곡에서 `track_peak > 1.0`(1.033) 확인 — 클리핑 방지(peak 메타데이터·`-k`) 다룰 때(5단계) 의미. 게인 산출엔 영향 없음.

**3단계 완료** (MP3 디코딩, PCM 추출). `gaindb/decode.py` — ffmpeg/ffprobe subprocess 로 MP3→PCM, (left, right, sample_rate) 반환, 원본 사양 스케일(±32768). 2단계 입력 공급. (1단계에서 CLI 로 언급된 `apply_gain.py` 는 2~4단계에서 확장됨.)

**4단계 완료·검증 완료** (태그 처리 — APE + ID3v2, 원본 전 기능 재현). 원본 사양 정리 완료(apetag.c/.h, id3tag.c/.h, mp3gain.c 의 changeGainAndTag/WriteMP3GainTag 검토 끝). 모듈: `gaindb/tag.py`(APE), `gaindb/id3.py`(ID3v2, tag.py 와 대칭 배치). 구현·검증 요약:

- **APE 읽기/쓰기/제거** (`tag.py`): `read_mp3gain_ape_tag`(파일 끝에서 APE/Lyrics3v2/ID3v1 꼬리 반복 감지·tag_offset 산출, 비-mp3gain 필드는 otherFields 원본 바이트로 보존; UNDO/MINMAX 고정 오프셋 슬라이싱; APE 푸터 오프셋 TagCount=16/Flags=20), `write_mp3gain_ape_tag`(헤더+푸터 재구성, otherFields 선배치 + mp3gain 필드 고정순서[MINMAX→ALBUM_MINMAX→UNDO→TRACK_GAIN→PEAK→ALBUM_GAIN→PEAK], Length/TagCount/Flags 갱신, 짧아지면 truncate, Lyrics3/ID3v1 꼬리 재기록, save_timestamp=os.utime), `remove_mp3gain_ape_tag`. 값 포맷 `%-+9.6f dB`/`%-8.6f`/`%03d,%03d`/`%+04d,%+04d,%c`. 검증: round-trip + mutagen 상호운용 + ID3v1 꼬리 보존.
- **scan_gain + change_gain_and_tag** (`writer.scan_gain` / `tag.change_gain_and_tag`): scan_gain 은 전 프레임 global_gain min/max(0 포함, 디코딩 없음 — MP3GAIN_MINMAX 원천). change_gain_and_tag 는 apply_gain 후 undo 누적[항상] + 좌우 동일 시 gain/peak/minmax 갱신(dB 차감 상수 1.505, peak ×2^(N/4), minmax 가감·wrap 시 정보폐기·비wrap 시 minGain 0-유지 클램프). 검증: scan (36,210), +3 적용 시 track_gain -8.095·peak 1.737·min/max 39/213·undo -3/-3, undo 원복 정확.
- **track_peak + auto/album 연결** (`analysis.track_peak` / `apply_gain.py`): track_peak 은 원본 find_maxsample 동등(좌우 abs max / 32768; 48k 곡 1.0335 재현). apply_gain.py 는 원본 main 순서로 분석(89dB raw)+track_peak+scan_gain → read 로 info 채우기[허용오차: gain 0.01dB, track peak 3.3, album peak 0.0001, min/max 불일치] → 스텝 양자화 → change_gain_and_tag 가 적용분 재차감. skip_tag 면 apply_gain 직접(원본 changeGain 분기). album 은 곡별 track 값 + album 값(누적·peak=곡별 max·minmax=곡별 min/max 의 min/max) 둘 다 채움. 검증: auto(-0.79→-1스텝, track_gain 0.715, min/max 35/209, undo 1,1; 원복 정확), album 2곡 44.1k+48k(-5.05→-3스텝, 두 곡 album 값 -0.535 공유, undo 3,3).
- **ID3v2 읽기/쓰기/제거** (`id3.py`): `read_mp3gain_id3_tag`(앞 ID3v2 → 끝 ID3v2.4 footer `3DI` → 끝 ID3v1; 끝 탐색 시 ID3v1/Lyrics3v2/APE 꼬리 스킵; 2.2/2.3/2.4 를 내부 2.4 로 통일 파싱: 업그레이드 테이블·unsync·ext header 스킵·프레임 드롭·2.3→2.4 DLEN 재정렬·2.2 PIC→APIC·TYER→TDRC; RVA2/TXXX/MP3GAIN 디코더, info=None 이면 매칭 판정만), `write_mp3gain_id3_tag`(항상 앞 단일 ID3v2.4·전체 unsync·ext header 없음·2KB 패딩·footer 없음; 기존 RG 프레임 제거 후 고정순서 append[ref_loudness "89.0 dB" → RVA2 track+TXXX track_gain → TXXX track_peak → RVA2 album+TXXX album_gain → TXXX album_peak → MINMAX → ALBUM_MINMAX → UNDO; TXXX desc 소문자, 인코딩 0/latin-1]; need_update 없으면 0 반환·무수정; 임시파일.TMP[version==0 이면 원본 전체 복사, 아니면 앞 ID3v2 만 들어내고 복사] → os.replace), `remove_mp3gain_id3_tag`(빈 info 로 write). 반환 규약: 1=기록, 0=변경불필요, 음수=에러. 값 포맷·게인 구조체·`_atof` 는 tag.py 재사용. 검증: read 5종(v2.4 full·RVA2-only·TXXX-only·v2.3·v1-only) + write 5종(round-trip·mutagen 상호운용·need_update=0·비-RG 프레임 보존·remove) 전부 PASS.
- **useId3 분기 래핑(⑤-C)** (`tag._write_mp3gain_tag` / `tag.read_mp3gain_tags`): 원본 WriteMP3GainTag 동등(use_id3 면 write_mp3gain_id3_tag 후 반환 >=0 이면 stale APE 제거; 아니면 APE 만 — 원본 비대칭 유지) + main 의 태그 읽기 분기 동등(APE 먼저 → use_id3 이고 APE 에 mp3gain 정보 있으면 dirty 로 업그레이드 강제 → ID3 로 덮어쓰기). change_gain_and_tag·apply_track_gain·apply_album_gain 에 use_id3 인자 추가, steps==0 분기도 래퍼 경유. id3 import 는 순환 회피 위해 함수 내부 지연. 검증(verify_5c.py): 11건 PASS — ID3 기록+stale APE 제거, undo 누적(-5,-5), APE→ID3 덮어쓰기·dirty 강제, APE 회귀 불변, 음수 반환 스킵.

검증 보조 스크립트/CLI: `inspect_tag.py`(APE 덤프), `verify_id3_read.py`/`verify_id3_write.py`/`verify_5c.py`(전부 git 제외·로컬 보존; fixture 생성부는 5단계 통합 테스트로 정식 등록 검토).

**4단계 → 5단계로 미룬 항목(축소 아님, 1.1 합의됨)**: 클리핑 경고·자동 클립(-k)·클립 질의(-c 미지정), directGain/directSingleChannelGain 의 태그 연동, recalc 비트마스크(FULL/AMP/MIN_MAX) 디코딩 스킵 최적화, CLI 진입점(_run_auto/_run_album)의 use_id3 노출(원본 -s i). 함수 레벨에서는 use_id3 인자를 이미 받음.

**4단계 1.1 미합의 메모(추후 합의)**: ① writer.apply_gain 의 single-channel 거부가 현재 mono(nchan==1)만 막고, 원본 changeGain 은 joint stereo 도 거부(mode 비트) — undo 가 좌우 다른 값을 적용할 수 있어 joint stereo 거부 추가 검토(결과 영향은 좌우 동일 게인 시 없음). ② MP3GainTagInfo 동적 속성 할당으로 오타가 조용히 통과 가능 — slots 적용 검토. ③ UTF-16(인코딩 1) TXXX 미인식은 원본 동일(원본도 인코딩 0/3 만 처리). ④ 48k 곡 track_peak>1.0(1.033) 관찰 — 클리핑 방지(-k) 다룰 때 의미, 게인 산출엔 영향 없음. ⑤ ID3 round-trip gain 정밀도는 RVA2 격자(/512·16bit)가 아닌 TXXX 6자리로 결정 — 원본 동일(둘 다 읽고 나중 TXXX 채택).

**5단계 묶음 A·B 완료·검증 완료** (CLI 옵션 파서 + 직접 게인 분기). 결과물: `mp3gain_cli.py`(통합 CLI 진입점, 루트).

- **묶음 A (옵션 파서 골격 + 즉시 동작 옵션)**: 원본 main 의 argv 순회 파서 동등 — 토큰이 정확히 2글자(`-x`/`/x`)일 때만 옵션, 인자는 다음 토큰, `file_start` 추적으로 `files` 산출. `Options`(`__slots__` 적용, 4단계 미합의 메모 ② 선제 차단). 즉시 동작: `-v`(버전), `-h`/`-?`(전체 도움말, `? wrap`→wrap 설명), `-q`, `-o`(databaseFormat + 세 갈래 헤더), `-p`, `-t`/`-T`(대소문자 구분). 나머지 옵션은 파싱만. 배너(버전·의존성)는 Gain dB/ffmpeg 에 맞게 조정(기능 출력은 원본 일치 — 사용자 합의).
- **묶음 B (직접 게인 실행 분기)**: `-g`(directGain, 양 채널 동일), `-l`(directSingleChannelGain, whichChannel 0=왼쪽/그외=오른쪽), `-u`(undoChanges, 태그 undo 기반 원복). 파일별 루프 + 태그 읽기 골격(`_read_tags`). 실행 분기 우선순위(원본 main 5.2) 자리 확보: checkTagOnly→undo→`-l`→`-g`→deleteTag→분석경로(C~D 미연결 안내).
- **부수 변경**: `frame.py` `FrameInfo`에 `mode` 필드 추가(0=stereo/1=joint/2=dual/3=mono). `writer.apply_gain` 단일 채널 거부를 mono(`nchan==1`)에서 `mode in (1,3)`(joint stereo·mono)로 확대 — 4단계 미합의 메모 ① 해소(원본 changeGain 의 `mode & 0x01` 거부 동등).
- **합의 사항(원본 동일 재현, 5.4)**: ① 붙여쓰기 인자 거부(다음 토큰만 인자, `-g5`는 파일명 취급) ② `-l` joint stereo/mono 거부 ③ `-l` whichChannel 0=왼쪽/그외=오른쪽 ④ `-c` 미지정 시 stdin y/n 질의(묶음 C 예정).
- 검증(verify_cli_ab.py, git 제외): 37 PASS / 0 FAIL. 옵션 파싱 25건(플래그·붙여쓰기·음수인자·`-l` 2인자·`-s` 서브옵션·미인식 경고·다중파일) + 두 음원에서 `-g` round-trip 복원·`-l` joint stereo 거부·`-u` undo 누적(-4)·원복.
- **미검증 메모**: 두 테스트 음원이 모두 joint stereo(mode=1)라 `-l` 정상 적용 경로(stereo/dual 에서 한쪽 채널만 변경)는 거부 경로만 확인됨. stereo/dual 음원 확보 시 정상 경로 추가 검증 필요(코드 결함 아님, 음원 한계).

**5단계 묶음 C-1 완료·검증 완료** (분석 경로 + 제안 출력). `mp3gain_cli.py` 에 분석 경로 추가(`_run_analysis`/`_analyze_one`/`_quantize_steps`/`_print_track_suggestion`/`_print_track_database`/`_print_album_suggestion`). decode_pcm→track_histogram·track_peak·scan_gain 으로 한 곡 분석, 단일 곡도 `gain_from_histograms([hist])` 로 Album 경로와 코드 공유. 원본 main 후반부 정합: dBGainMod(-d)는 양자화 전 dB 에, mp3GainMod(-m)는 양자화 후 스텝에 가산; Track 클립 경고 `maxsample*2^(steps/4)>32767.0`, Album 곡별 `peak*2^(steps/4)>1.0`; maxAmpOnly(-x) 시 dBchange=0 이되 출력 형식 동일; Album 조건 `files>1 && !applyTrack && !analysisTrack`; NOT_ENOUGH_SAMPLES 시 해당 파일 stderr 메시지 후 제안·집계 제외; `-r/-a` 켜지면 비-database 제안 억제(원본 `if(!applyTrack&&!applyAlbum)`). 출력 `%f`=6자리, track_peak 는 출력 직전 ×32768 환원. **진행률 표시 생략**(ffmpeg 일괄 디코딩이라는 디코더 예외의 귀결 — 원본 기능 축소 아님, 1.1·7 합의 디코더 예외의 부수 효과). 검증(verify_cli_c1.py, git 제외): 39 PASS / 0 FAIL. 두 곡 Track dB 는 ffmpeg replaygain 실측(10cm 48k -6.03 / Debussy 44.1k -0.77)과 0.02dB 이내 대조 확인.

**C-1 → C-2/C-3 으로 미룬 항목(축소 아님, 1.1 합의됨)**: `-r`(Track 적용)·`-a`(Album 적용)의 실제 changeGainAndTag 호출, intGainChange==0 시 "No changes…/tag needs update" 분기, 적용 후 태그 갱신(C-2). 클립 `-k`(autoClip: Track `floor(4*log10(32767/maxsample)/log10(2))`, Album `floor(-4*log10(maxmaxsample)/log10(2))`)·`-c` 미지정 시 stdin y/n 질의(queryUserForClipping)(C-3). C-1 은 분석·제안 출력만 수행하고 적용 진입 시 stderr 로 C-2 안내.

**다음 = 5단계 묶음 C-2 (`-r`/`-a` 적용).** C-1 의 `_run_analysis` 에 적용 단계를 연결한다 — applyTrack 이면 곡별 제안 스텝으로 `change_gain_and_tag`(skip_tag 면 `apply_gain`) 호출, intGainChange==0 시 "No changes are necessary"(+dirty 면 태그만 갱신) 분기; applyAlbum 이면 Album 집계 후 전 곡에 동일 스텝 적용. 원본 main 후반부의 적용 순서·문구(`Applying mp3 gain change of N to …`) 재현. **검증 시 원본 음원 보존을 위해 임시 복사본에서 round-trip 복원 확인 필수**(C-2 시작 시 챙김). 이후 C-3(클립 `-k`/`-c` stdin 질의) → 묶음 D(태그 모드 `-s c/d/s/r/u/i/a` + recalc 비트마스크 + 일괄/Album 집계 연결, scan_gain.py·inspect_tag.py·apply_gain.py 흡수).

- 로컬에 미커밋 변경분이 생기면 첫 메시지에 함께 알린다.
