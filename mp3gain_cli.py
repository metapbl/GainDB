"""
mp3gain_cli.py - Gain dB 통합 CLI (원본 mp3gain 옵션 체계 재현)

원본 mp3gain.c 의 main() 옵션 파싱·실행 분기와 동등하게 구현한다.

[묶음 A] 옵션 파서 골격 + 즉시 동작 옵션(-v/-h/-?/-q/-o/-p/-t/-T).
[묶음 B] 직접 게인 실행 분기: -u(undo) / -l(단일 채널) / -g(전체 게인).
[묶음 C-1] 분석 경로 + 제안 출력(-r/-a/-e/-x/-m/-d/-o).
[묶음 C-2] -r(Track 적용)/-a(Album 적용) 연결(길 B, 단일 디코딩 패스).
[묶음 C-3] 클립 처리: -k(autoClip) + -c 미지정 시 stdin y/n 질의
           (queryUserForClipping). Track autoClip 상한
           floor(4*log10(32767/maxsample)/log10(2)), Album autoClip 상한
           floor(-4*log10(maxmaxsample)/log10(2)). Album autoClip 하향은 전 곡
           루프 밖에서 단일 스텝에 한 번만(원본 /*MAA*/ 위치). 클립 질의 문구는
           원본 영어 그대로. 입력은 input() 기반 등가(첫 글자 Y/N, EOF→N).

[묶음 D-1] -s c(checkTagOnly) + -s d(deleteTag).
[묶음 D-2] -s r(forceRecalculateTag)/-s u(forceUpdateTag) + recalc 비트마스크
           디코딩 스킵 + "update file tags" 블록.
  - forceUpdateTag: 전 파일 태그를 읽기 전 dirty 로 초기화(원본 tagInfo[].dirty
    = forceUpdateTag). 읽은 뒤에도 dirty 유지.
  - forceRecalculateTag: 태그 읽은 뒤 album/track gain·peak·minmax 의 have_* 를
    끄고 각각 dirty. undo 는 보존(원본 "NOT Undo information!").
  - recalc 비트마스크(FULL=1/AMP=2/MIN_MAX=4): 전 파일 태그 선행 읽기 후,
    album_recalc = (force_recalc or skip_tag) ? FULL : 0. force_recalc/skip/
    delete 가 아니면 첫 파일 album 값을 기준으로 곡별 track recalc(have_track_*
    없으면 비트 켬)와 album_recalc(have_album_* 없거나 첫 파일과 != 면 비트 켬)를
    채운다. maxAmpOnly 면 gain 검사 스킵. 마지막에 각 곡 recalc |= album_recalc.
  - 디코딩 스킵(ffmpeg 디코더 예외의 귀결, 1.1·7 합의): recalc==0 → ffmpeg·
    scan_gain 모두 스킵(태그값 사용). recalc&(FULL|AMP) → ffmpeg 1회(FULL 이면
    라우드니스, 아니면 trackGain 유지; peak 은 AMP/FULL 이면 ffmpeg 결과, 아니면
    태그값). recalc&MIN_MAX 만 → ffmpeg 없이 scan_gain 만. 결과 수치는 원본 동일,
    디코딩 횟수만 다름(decode_pcm 전부-아니면-전무).
  - Album recalc 의 curAlbum* 비교는 원본 그대로 부동소수 정확 일치(!=) 사용
    (clean-room 재현, epsilon 미도입).
  - "update file tags": 순수 분석 경로(적용/직접/삭제/skip/check 모두 아님)에서
    dirty 곡의 태그만 기록(원본 끝 블록).

[원본 동일 재현 합의 사항 (CLAUDE.md 5.4)]
- 붙여쓰기 인자 거부: 토큰이 정확히 2글자일 때만 옵션. 인자는 항상 다음 토큰.
- -l joint stereo/mono 거부: writer.apply_gain 이 mode 1·3 거부(묶음 B 적용).
- -l whichChannel: 0=왼쪽, 그 외=오른쪽(원본 if(whichChannel) 동등).
- -c 미지정 시 stdin y/n 클립 질의(묶음 C-3).

[실행 분기 우선순위 (원본 main 5.2)]
  checkTagOnly → undoChanges → directSingleChannelGain → directGain
  → deleteTag → 분석 경로(C-3: 분석·제안·적용·클립까지).

[C-1/C-2/C-3 의 원본 정합 포인트]
- dBGainMod(-d)는 양자화 전 dB 에 더하고, mp3GainMod(-m)는 양자화 후 스텝에 더함.
- Track 클립 경고/질의: maxsample * 2^(steps/4) > 32767.0.
- Album 곡별 클립 경고/질의: trackPeak * 2^(steps/4) > 1.0 (단위 다름에 유의).
- maxAmpOnly(-x): dBchange=0 으로 두되 제안 출력 형식은 그대로.
- Album 조건: 파일 2개 이상 and not apply_track and not analysis_track.
- NOT_ENOUGH_SAMPLES: 해당 파일 stderr 메시지 후 제안·Album 집계에서 제외.
- 적용(C-2): intGainChange==0 → "No changes…/tag needs update", !=0 → 적용.
- 클립(C-3): autoClip 은 하향만(상한보다 클 때). autoClip 아니고 !ignoreClip 이면
  클립 조건 충족 시에만 질의. 질의 거부면 goAhead=0(미적용, dirty 면 태그만).

[배너 조정] mpglib/저작권/프로그램명 배너는 Gain dB(ffmpeg 기반)에 맞게 조정.
기능 출력(-o, 분석 수치, 태그, 적용/클립 문구)은 원본 일치.
"""

import sys
from math import pow, log10, floor

from gaindb.writer import apply_gain, scan_gain
from gaindb.tag import (
    read_mp3gain_tags,
    change_gain_and_tag,
    _write_mp3gain_tag,
    remove_mp3gain_ape_tag,
)
from gaindb.decode import decode_pcm, DecodeError
from gaindb.analysis import (
    track_histogram,
    gain_from_histograms,
    track_peak,
    db_to_steps,
    NOT_ENOUGH_SAMPLES,
)
from apply_gain import _fill_track_info, _fill_album_info

VERSION = "0.5.0-dev"
PROGNAME = "Gain dB"

# 원본 recalc 비트마스크 (mp3gain.c).
FULL_RECALC = 1
AMP_RECALC = 2
MIN_MAX_GAIN_RECALC = 4

# 원본 SWITCH_CHAR: Windows 는 '/' 와 '-' 둘 다, 그 외는 '-'.
# 우리는 양쪽을 모두 옵션 접두로 허용한다(원본 WIN32 분기 동등).
_SWITCH_CHARS = ("-", "/")


class Options:
    """파싱된 전역 옵션 모음. 원본 main 의 전역 플래그들과 1:1 대응."""

    __slots__ = (
        "apply_track", "apply_album", "analysis_track",
        "ignore_clip_warning", "auto_clip",
        "direct_gain", "direct_single_channel_gain", "direct_gain_val",
        "which_channel",
        "mp3_gain_mod", "db_gain_mod",
        "database_format", "using_temp", "quiet_mode", "save_time",
        "max_amp_only", "reckless", "wrap_gain", "undo_changes",
        "skip_tag", "delete_tag", "force_recalculate_tag",
        "force_update_tag", "check_tag_only", "use_id3",
        "files", "file_start",
    )

    def __init__(self):
        # 게인 모드
        self.apply_track = False           # -r
        self.apply_album = False           # -a
        self.analysis_track = False        # -e
        # 클리핑
        self.ignore_clip_warning = False   # -c
        self.auto_clip = False             # -k
        # 직접 게인
        self.direct_gain = False           # -g
        self.direct_single_channel_gain = False  # -l
        self.direct_gain_val = 0
        self.which_channel = 0
        # 게인 보정
        self.mp3_gain_mod = 0              # -m
        self.db_gain_mod = 0.0             # -d
        # 출력/동작 플래그
        self.database_format = False       # -o
        self.using_temp = True             # -t(기본) / -T
        self.quiet_mode = False            # -q
        self.save_time = False             # -p
        self.max_amp_only = False          # -x
        self.reckless = False              # -f
        self.wrap_gain = False             # -w
        self.undo_changes = False          # -u
        # 태그 모드 (-s ...)
        self.skip_tag = False              # -s s
        self.delete_tag = False            # -s d
        self.force_recalculate_tag = False  # -s r
        self.force_update_tag = False      # -s u
        self.check_tag_only = False        # -s c
        self.use_id3 = False               # -s i / -s a
        # 입력 파일
        self.files = []
        self.file_start = 1


def _show_version(out=sys.stderr):
    print(f"{PROGNAME} version {VERSION}", file=out)
    print("MP3Gain 호환 무손실 음량 조정 도구 (clean-room 재구현)", file=out)
    print("PCM 디코딩에 ffmpeg 를 사용 (PATH 에서 호출)", file=out)


def _err_usage():
    """원본 errUsage 동등: 짧은 사용법 + 종료코드 1."""
    _show_version()
    print(f"사용법: {PROGNAME} [options] <infile> [<infile 2> ...]", file=sys.stderr)
    print("  전체 옵션 목록은 -? 또는 -h 로 확인", file=sys.stderr)
    sys.exit(1)


def _wrap_explanation():
    """원본 wrapExplanation 동등: -w 동작 설명 후 종료."""
    e = sys.stderr
    print("문제의 핵심:", file=e)
    print("mp3gain 이 조정하는 \"global gain\" 필드는 8비트 부호없는 정수라", file=e)
    print("가능한 값은 0~255 입니다.", file=e)
    print("", file=e)
    print("대부분의 mp3 파일은 230 을 넘지 않아 위쪽 여유는 충분합니다", file=e)
    print("(재생음을 키우는 방향은 거의 문제가 없습니다).", file=e)
    print("", file=e)
    print("문제는 범위의 아래쪽입니다. 일부 인코더는 무음 프레임의", file=e)
    print("global gain 을 0 으로 만듭니다. 이때 게인을 1 낮추면?", file=e)
    print("과거 mp3gain 은 결과를 255 로 wrap 했습니다. 그래야 같은 양만큼", file=e)
    print("낮췄다 올리면 mp3 가 정확히 원래대로 돌아오기 때문입니다.", file=e)
    print("", file=e)
    print("하지만 0-게인 프레임에 실제 오디오 데이터를 넣는 인코더가 있어,", file=e)
    print("그런 파일의 게인을 낮추면 global gain 이 갑자기 커져 재생 시", file=e)
    print("짧고 매우 큰 잡음이 날 수 있습니다.", file=e)
    print("", file=e)
    print("그래서 현재 기본 동작은 wrap 하지 않는 것입니다:", file=e)
    print("1) 게인 변경으로 프레임 global gain 이 0 아래로 가면 0 으로 고정", file=e)
    print("2) 255 위로 가면 255 로 고정", file=e)
    print("3) 이미 0 인 프레임은 양수 변경이라도 그대로 둠", file=e)
    print("", file=e)
    print("원래의 \"wrapping\" 동작을 쓰려면 -w 스위치를 사용하세요.", file=e)
    sys.exit(0)


def _full_usage():
    """원본 fullUsage 동등: 전체 옵션 목록 후 종료."""
    _show_version()
    e = sys.stderr
    print(f"사용법: {PROGNAME} [options] <infile> [<infile 2> ...]", file=e)
    print("옵션:", file=e)
    print("\t-v - 버전 번호 표시", file=e)
    print("\t-g <i>  - 분석 없이 게인 i 적용", file=e)
    print("\t-l 0 <i> - 분석 없이 채널 0(왼쪽)에만 게인 i 적용", file=e)
    print("\t          (STEREO 파일만, Joint Stereo 불가)", file=e)
    print("\t-l 1 <i> - 분석 없이 채널 1(오른쪽)에만 게인 i 적용", file=e)
    print("\t-e - 여러 파일이어도 Album 분석 생략", file=e)
    print("\t-r - Track 게인 자동 적용(모든 파일을 동일 음량으로)", file=e)
    print("\t-k - 클리핑이 없도록 Track/Album 게인 자동 하향", file=e)
    print("\t-a - Album 게인 자동 적용(같은 앨범의 파일들: 상대 음량은", file=e)
    print("\t              유지한 채 앨범 평균 음량을 정규화)", file=e)
    print("\t-m <i> - 제안 MP3 게인을 정수 i 만큼 보정", file=e)
    print("\t-d <n> - 제안 dB 게인을 실수 n 만큼 보정", file=e)
    print("\t-c - 게인 적용 시 클리핑 경고 무시", file=e)
    print("\t-o - 출력을 데이터베이스 친화적 탭 구분 목록으로", file=e)
    print("\t-t - 수정본을 임시 파일에 쓴 뒤 원본을 대체(기본)", file=e)
    print("\t-T - 원본 파일을 직접 수정(-t 의 반대)", file=e)
    print("\t-q - 조용히: 상태 메시지 없음", file=e)
    print("\t-p - 원본 파일 타임스탬프 보존", file=e)
    print("\t-x - 파일의 최대 진폭만 탐색", file=e)
    print("\t-f - 입력을 MPEG 2 Layer III 로 가정(Layer I/II 오인 검사 생략)", file=e)
    print("\t-? 또는 -h - 이 메시지 표시", file=e)
    print("\t-s c - 저장된 태그 정보만 확인(다른 처리 없음)", file=e)
    print("\t-s d - 저장된 태그 정보 삭제(다른 처리 없음)", file=e)
    print("\t-s s - 저장된 태그 정보 무시(읽지도 쓰지도 않음)", file=e)
    print("\t-s r - 강제 재계산(태그 정보를 읽지 않음)", file=e)
    print("\t-s u - 강제 업데이트(태그를 dirty 로 표시해 갱신)", file=e)
    print("\t-s i - MP3 게인 정보에 ID3v2 태그 사용", file=e)
    print("\t-s a - MP3 게인 정보에 APE 태그 사용(기본)", file=e)
    print("\t-u - 변경 되돌리기(저장된 태그 정보 기반)", file=e)
    print("\t-w - gain+change 가 255 초과/0 미만이면 \"wrap\"", file=e)
    print("\t      (\"-? wrap\" 으로 전체 설명 확인)", file=e)
    print("-r 과 -a 를 함께 지정하면 두 번째 것만 동작합니다", file=e)
    print("-c 를 지정하지 않으면 클립 가능성이 있는 파일에", file=e)
    print("     게인을 적용하기 전 멈추고 물어봅니다", file=e)
    sys.exit(0)


def _atof(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def _atoi(s):
    # 원본 atoi: 선두 정수만 취하고 실패 시 0. 간이 재현.
    s = s.strip()
    sign = 1
    i = 0
    if i < len(s) and s[i] in "+-":
        if s[i] == "-":
            sign = -1
        i += 1
    j = i
    while j < len(s) and s[j].isdigit():
        j += 1
    if j == i:
        return 0
    return sign * int(s[i:j])


def _next_arg(argv, i, opt):
    """다음 토큰을 인자로 가져온다. 없으면 errUsage(종료)."""
    if i + 1 < len(argv):
        return argv[i + 1], i + 1
    _err_usage()


def parse_args(argv):
    """원본 main 의 옵션 파싱 루프 동등. Options 를 반환한다.

    argv 는 프로그램명을 포함한 전체 리스트(argv[0] 는 무시).
    """
    opt = Options()
    file_start = 1
    i = 1
    n = len(argv)

    while i < n:
        tok = argv[i]
        # 옵션 인식: 접두가 '-' 또는 '/' 이고 길이가 정확히 2.
        is_option = (len(tok) == 2 and tok[0] in _SWITCH_CHARS)
        if not is_option:
            i += 1
            continue

        c = tok[1].lower()
        file_start += 1

        if c == "a":
            opt.apply_track = False
            opt.apply_album = True
        elif c == "c":
            opt.ignore_clip_warning = True
        elif c == "d":
            val, i = _next_arg(argv, i, "d")
            opt.db_gain_mod = _atof(val)
            file_start += 1
        elif c == "f":
            opt.reckless = True
        elif c == "g":
            opt.direct_gain = True
            opt.direct_single_channel_gain = False
            val, i = _next_arg(argv, i, "g")
            opt.direct_gain_val = _atoi(val)
            file_start += 1
        elif c in ("h", "?"):
            # '-? wrap' 또는 '-h wrap' → wrap 설명. 그 외 → 전체 도움말.
            if i + 1 < n and argv[i + 1][:1].lower() == "w":
                _wrap_explanation()
            _full_usage()
        elif c == "k":
            opt.auto_clip = True
        elif c == "l":
            opt.direct_single_channel_gain = True
            opt.direct_gain = False
            # 인자 2개: 채널, 게인값 (모두 다음 토큰).
            ch_val, i = _next_arg(argv, i, "l")
            opt.which_channel = _atoi(ch_val)
            file_start += 1
            g_val, i = _next_arg(argv, i, "l")
            opt.direct_gain_val = _atoi(g_val)
            file_start += 1
        elif c == "m":
            val, i = _next_arg(argv, i, "m")
            opt.mp3_gain_mod = _atoi(val)
            file_start += 1
        elif c == "o":
            opt.database_format = True
        elif c == "p":
            opt.save_time = True
        elif c == "q":
            opt.quiet_mode = True
        elif c == "r":
            opt.apply_track = True
            opt.apply_album = False
        elif c == "s":
            sub, i = _next_arg(argv, i, "s")
            file_start += 1
            sc = sub[:1].lower()
            if sc == "c":
                opt.check_tag_only = True
            elif sc == "d":
                opt.delete_tag = True
            elif sc == "s":
                opt.skip_tag = True
            elif sc == "u":
                opt.force_update_tag = True
            elif sc == "r":
                opt.force_recalculate_tag = True
            elif sc == "i":
                opt.use_id3 = True
            elif sc == "a":
                opt.use_id3 = False
            else:
                _err_usage()
        elif tok[1] == "t":   # 소문자 t: temp 사용
            opt.using_temp = True
        elif tok[1] == "T":   # 대문자 T: 직접 수정
            opt.using_temp = False
        elif c == "u":
            opt.undo_changes = True
        elif c == "v":
            _show_version()
            sys.exit(0)
        elif c == "w":
            opt.wrap_gain = True
        elif c == "x":
            opt.max_amp_only = True
        elif c == "e":
            opt.analysis_track = True
        else:
            # 원본: 인식 못 한 옵션은 경고만 내고 계속(fileStart 는 이미 증가).
            print(f"옵션 {tok} 을(를) 인식하지 못했습니다", file=sys.stderr)

        i += 1

    opt.file_start = file_start
    opt.files = argv[file_start:]
    return opt


def _print_database_header(opt):
    """원본 main 초반의 -o 헤더 세 갈래 동등."""
    if opt.check_tag_only:
        print("File\tMP3 gain\tdB gain\tMax Amplitude\tMax global_gain\t"
              "Min global_gain\tAlbum gain\tAlbum dB gain\tAlbum Max Amplitude\t"
              "Album Max global_gain\tAlbum Min global_gain")
    elif opt.undo_changes:
        print("File\tleft global_gain change\tright global_gain change")
    else:
        print("File\tMP3 gain\tdB gain\tMax Amplitude\tMax global_gain\t"
              "Min global_gain")
    sys.stdout.flush()


def _clear_for_recalc(info):
    """원본 forceRecalculateTag 처리 동등.

    album/track 의 gain·peak·minmax 중 켜진 게 있으면 그것마다 dirty 를 켜고 끈다.
    undo 정보는 보존한다(원본 주석 "NOT Undo information!").
    """
    if info.have_album_gain:
        info.dirty = True
        info.have_album_gain = False
    if info.have_album_peak:
        info.dirty = True
        info.have_album_peak = False
    if info.have_track_gain:
        info.dirty = True
        info.have_track_gain = False
    if info.have_track_peak:
        info.dirty = True
        info.have_track_peak = False
    if info.have_min_max_gain:
        info.dirty = True
        info.have_min_max_gain = False
    if info.have_album_min_max_gain:
        info.dirty = True
        info.have_album_min_max_gain = False


def _read_all_tags(opt):
    """원본 main 의 '전 파일 태그 선행 읽기' 동등.

    각 파일의 (info, file_tags) 를 미리 읽어둔다(recalc 비트마스크 계산과 곡별
    스킵 판정에 필요). 원본 순서:
      - dirty 를 forceUpdateTag 로 초기화(태그 읽기 전).
      - (not skip_tag and not delete_tag) 일 때만 실제로 읽는다. 그 외엔 빈 info.
      - forceRecalculateTag 면 읽은 뒤 _clear_for_recalc.

    반환: {path: (info, file_tags)} (입력 순서 보존을 위해 리스트로도 들고 다님).
    """
    from gaindb.tag import MP3GainTagInfo, FileTags

    tags = {}
    for path in opt.files:
        if opt.skip_tag or opt.delete_tag:
            # 태그를 읽지 않음. 빈 info(원본 calloc 동등)에 dirty 만 force_update 반영.
            info = MP3GainTagInfo()
            info.dirty = opt.force_update_tag
            tags[path] = (info, FileTags())
            continue

        info, file_tags = read_mp3gain_tags(path, opt.use_id3)
        info.dirty = info.dirty or opt.force_update_tag
        if opt.force_recalculate_tag:
            _clear_for_recalc(info)
        tags[path] = (info, file_tags)
    return tags


def _compute_recalc(opt, tags):
    """원본 main 의 recalc 비트마스크 계산 동등.

    album_recalc = (force_recalc or skip_tag) ? FULL : 0.
    not skip_tag and not delete_tag and not force_recalc 일 때만 '이미 가진 정보로
    충분한지' 검사: 곡별 info.recalc(track 쪽)와 album_recalc(album 쪽)에 비트를 켠다.
    Album 검사는 '파일 2개 이상 and not apply_track and not analysis_track' 일 때만.
    curAlbum* 비교는 원본 그대로 부동소수 정확 일치(!=). 마지막에 각 곡
    info.recalc |= album_recalc.

    반환: album_recalc (전 곡 info.recalc 에는 이미 반영해 둠).
    """
    files = opt.files
    multi = len(files) > 1
    album_check = multi and (not opt.apply_track) and (not opt.analysis_track)

    album_recalc = FULL_RECALC if (opt.force_recalculate_tag or opt.skip_tag) else 0

    if (not opt.skip_tag) and (not opt.delete_tag) and (not opt.force_recalculate_tag):
        # 첫 파일 album 값 기준(원본: tagInfo[fileStart].album*).
        first_info = tags[files[0]][0]
        cur_album_gain = first_info.album_gain
        cur_album_peak = first_info.album_peak
        cur_album_min = first_info.album_min_gain
        cur_album_max = first_info.album_max_gain

        for path in files:
            info = tags[path][0]
            if not opt.max_amp_only:
                # gain 관련 검사 (maxAmpOnly 면 스킵).
                if album_check:
                    if (not info.have_album_gain) or (info.album_gain != cur_album_gain):
                        album_recalc |= FULL_RECALC
                if not info.have_track_gain:
                    info.recalc |= FULL_RECALC
            if album_check:
                if (not info.have_album_peak) or (info.album_peak != cur_album_peak):
                    album_recalc |= AMP_RECALC
                if (not info.have_album_min_max_gain) or \
                        (info.album_max_gain != cur_album_max) or \
                        (info.album_min_gain != cur_album_min):
                    album_recalc |= MIN_MAX_GAIN_RECALC
            if not info.have_track_peak:
                info.recalc |= AMP_RECALC
            if not info.have_min_max_gain:
                info.recalc |= MIN_MAX_GAIN_RECALC

    # album recalc 를 각 곡에 전파(원본: tagInfo[].recalc |= albumRecalc).
    for path in files:
        tags[path][0].recalc |= album_recalc

    return album_recalc


# ------------------------------------------------------------------
# [묶음 B] 직접 게인 / undo
# ------------------------------------------------------------------

def _run_undo(opt, path, info, file_tags):
    """원본 undoChanges 분기 동등.

    태그의 undo 정보로 역방향 게인을 적용한다. 원본은 directGain 을 켜서
    이중 태그 기록을 막지만, 우리는 change_gain_and_tag 가 한 번에 적용+기록.
    """
    have_undo = info is not None and info.have_undo
    nonzero = have_undo and (info.undo_left or info.undo_right)

    if nonzero:
        if (not opt.quiet_mode) and (not opt.database_format):
            print(f"mp3gain 변경 되돌리는 중 ({info.undo_left},{info.undo_right}) "
                  f"-> {path} ...", file=sys.stderr)
        if opt.database_format:
            print(f"{path}\t{info.undo_left}\t{info.undo_right}")
        change_gain_and_tag(path, info.undo_left, info.undo_right,
                            info, file_tags, wrap=opt.wrap_gain,
                            use_id3=opt.use_id3)
        return 0
    else:
        if opt.database_format:
            print(f"{path}\t0\t0")
        elif not opt.quiet_mode:
            if have_undo:
                print(f"{path} 에 되돌릴 변경이 없습니다", file=sys.stderr)
            else:
                print(f"{path} 에 undo 정보가 없습니다", file=sys.stderr)
        return 1


def _run_direct_single(opt, path, info, file_tags):
    """원본 directSingleChannelGain 분기 동등(-l).

    whichChannel: 0=왼쪽, 그 외=오른쪽. stereo/dual 채널에서만 허용
    (writer 가 joint stereo·mono 거부).
    """
    val = opt.direct_gain_val
    if not opt.quiet_mode:
        print(f"채널 {opt.which_channel} 에 게인 {val} 적용 중 -> {path} ...",
              file=sys.stderr)

    if opt.which_channel:   # 0 이 아니면 오른쪽
        left, right = 0, val
    else:                   # 0 이면 왼쪽
        left, right = val, 0

    if opt.skip_tag:
        apply_gain(path, left, right, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, left, right, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("완료", file=sys.stderr)
    return 0


def _run_direct(opt, path, info, file_tags):
    """원본 directGain 분기 동등(-g). 양 채널에 동일 게인."""
    val = opt.direct_gain_val
    if not opt.quiet_mode:
        print(f"게인 {val} 적용 중 -> {path} ...", file=sys.stderr)

    if opt.skip_tag:
        apply_gain(path, val, val, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, val, val, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("완료", file=sys.stderr)
    return 0


# ------------------------------------------------------------------
# [묶음 C-1/C-2/C-3] 분석 경로 + 제안 출력 + 적용 + 클립
# ------------------------------------------------------------------

def _quantize_steps(db_change, opt):
    """원본 main 의 dB→스텝 양자화 순서 동등.

    dBGainMod(-d)는 양자화 전 dB 에 더하고, db_to_steps 로 양자화한 뒤
    mp3GainMod(-m)를 스텝에 더한다. 반환: (보정된 dBchange, intGainChange).
    """
    db_change += opt.db_gain_mod
    steps = db_to_steps(db_change)
    steps += opt.mp3_gain_mod
    return db_change, steps


def _query_user_for_clipping(path, steps):
    """원본 queryUserForClipping 동등(stdin y/n 질의).

    "WARNING: %s may clip with mp3 gain change %d" 경고 후 "Make change? [y/n]:"
    로 반복 질의. 첫 글자 Y → True, N → False. EOF(EOFError)면 N(=False).
    원본은 getchar() 한 글자씩이지만 input() 한 줄의 첫 글자로 등가 재현한다.

    반환: 적용하면 True, 거부하면 False.
    """
    print(f"\nWARNING: {path} may clip with mp3 gain change {steps}",
          file=sys.stderr)
    sys.stdout.flush()
    sys.stderr.flush()
    while True:
        print("Make change? [y/n]:", end="", file=sys.stderr)
        sys.stderr.flush()
        try:
            line = input()
        except EOFError:
            return False  # 원본: EOF → 'N'
        ch = line[:1].upper()
        if ch == "Y":
            return True
        if ch == "N":
            return False
        # Y/N 아니면 다시 묻는다(원본 while 루프 동등).


def _auto_clip_track(steps, max_sample):
    """원본 Track autoClip 동등.

    intMaxNoClipGain = floor(4*log10(32767/maxsample)/log10(2)). 제안 스텝이
    이보다 크면 하향한다. 하향하면 (새 스텝, True), 아니면 (원 스텝, False).
    """
    if max_sample <= 0:
        return steps, False
    max_no_clip = int(floor(4.0 * log10(32767.0 / max_sample) / log10(2.0)))
    if steps > max_no_clip:
        return max_no_clip, True
    return steps, False


def _auto_clip_album(steps, max_max_sample):
    """원본 Album autoClip 동등.

    intMaxNoClipGain = floor(-4*log10(maxmaxsample)/log10(2)) (maxmaxsample 은
    정규화 album peak). 제안 스텝이 이보다 크면 하향. 전 곡 루프 밖에서 한 번만
    호출한다. 하향하면 (새 스텝, True), 아니면 (원 스텝, False).
    """
    if max_max_sample <= 0:
        return steps, False
    max_no_clip = int(floor(-4.0 * log10(max_max_sample) / log10(2.0)))
    if steps > max_no_clip:
        return max_no_clip, True
    return steps, False


def _analyze_one(opt, path, info, file_tags):
    """한 곡을 분석해 분석 수치 + 태그(info/file_tags)를 반환한다.

    info.recalc 비트에 따라 디코딩(ffmpeg)·scan_gain 호출을 스킵한다(D-2,
    ffmpeg 디코더 예외의 귀결 — 1.1·7 합의). 결과 수치는 원본과 동일.

    반환: (hist, peak, min_gain, max_gain, raw_db, info, file_tags)
      - hist: 라우드니스 히스토그램(FULL 재계산이 아니면 None).
      - peak: 정규화 peak(0~1, 1.0 초과 가능).
      - min_gain, max_gain: 프레임 global_gain min/max.
      - raw_db: 89dB 기준 Track dB. maxAmpOnly 면 0.0, FULL 아니면 태그값,
                샘플 부족이면 NOT_ENOUGH_SAMPLES.

    recalc 별 동작:
      - recalc == 0: ffmpeg·scan_gain 모두 스킵. 전부 태그값
        (track_gain, track_peak, min/max). hist=None.
      - recalc & (FULL|AMP): ffmpeg 1회. peak 는 ffmpeg 결과.
        FULL 이면 라우드니스(hist) 계산해 raw_db 산출, 아니면 태그 track_gain.
      - recalc & MIN_MAX 만 (FULL/AMP 아님): ffmpeg 없이 scan_gain 만.
        peak·raw_db 는 태그값.

    분석 불가(DecodeError)면 None 을 반환한다.
    """
    recalc = info.recalc if info is not None else FULL_RECALC
    need_decode = bool(recalc & (FULL_RECALC | AMP_RECALC))
    need_scan = bool(recalc & MIN_MAX_GAIN_RECALC)

    # --- peak: 디코딩하면 ffmpeg 결과, 아니면 태그값 ---
    left = right = sample_rate = None
    if need_decode:
        try:
            left, right, sample_rate = decode_pcm(path)
        except DecodeError as exc:
            print(f"{path} 분석 실패: {exc}", file=sys.stderr)
            return None
        peak = track_peak(left, right)
    else:
        peak = info.track_peak if (info is not None and info.have_track_peak) else 0.0

    # --- min/max global_gain: 스캔하면 scan_gain, 아니면 태그값 ---
    if need_scan:
        min_gain, max_gain = scan_gain(path)
        if min_gain is None:
            min_gain = 0
        if max_gain is None:
            max_gain = 0
    else:
        min_gain = info.min_gain if (info is not None and info.have_min_max_gain) else 0
        max_gain = info.max_gain if (info is not None and info.have_min_max_gain) else 0

    # --- maxAmpOnly: dB 분석 안 함 ---
    if opt.max_amp_only:
        return (None, peak, min_gain, max_gain, 0.0, info, file_tags)

    # --- raw_db: FULL 이면 라우드니스 계산, 아니면 태그 track_gain ---
    if recalc & FULL_RECALC:
        hist = track_histogram(left, right, sample_rate)
        raw = gain_from_histograms([hist])  # 단일 곡도 Album 경로와 코드 공유
        if raw is NOT_ENOUGH_SAMPLES:
            return (hist, peak, min_gain, max_gain, NOT_ENOUGH_SAMPLES,
                    info, file_tags)
    else:
        hist = None
        raw = info.track_gain if (info is not None and info.have_track_gain) else 0.0

    # 분석 성공 → info 에 89dB 기준 track 값 채우기(원본 curTag 갱신 동등).
    if info is not None:
        _fill_track_info(info, raw, peak, min_gain, max_gain)

    return (hist, peak, min_gain, max_gain, raw, info, file_tags)


def _print_track_suggestion(opt, db_change, steps, max_sample, max_gain, min_gain):
    """원본 비-database Track 제안 출력 동등(stdout, %f=6자리)."""
    print(f'Recommended "Track" dB change: {db_change:f}')
    print(f'Recommended "Track" mp3 gain change: {steps}')
    if max_sample * pow(2.0, steps / 4.0) > 32767.0:
        print("WARNING: some clipping may occur with this gain change!")
    print(f"Max PCM sample at current gain: {max_sample:f}")
    print(f"Max mp3 global gain field: {max_gain}")
    print(f"Min mp3 global gain field: {min_gain}")
    print("")


def _print_track_database(opt, path, steps, db_change, max_sample, max_gain, min_gain):
    """원본 database Track 한 줄 동등."""
    print(f"{path}\t{steps}\t{db_change:f}\t{max_sample:f}\t{max_gain}\t{min_gain}")
    sys.stdout.flush()


def _print_album_suggestion(opt, db_change, steps, results):
    """원본 비-database Album 제안 출력 동등.

    results: (path, hist, peak, min_gain, max_gain, info, file_tags) 의 리스트.
    곡별 클립 경고는 trackPeak * 2^(steps/4) > 1.0 기준(원본과 동일 단위).
    """
    print("")
    print(f'Recommended "Album" dB change for all files: {db_change:f}')
    print(f'Recommended "Album" mp3 gain change for all files: {steps}')
    for path, _hist, peak, _min_g, _max_g, _info, _ft in results:
        if peak * pow(2.0, steps / 4.0) > 1.0:
            print(f"WARNING: with this global gain change, "
                  f"some clipping may occur in file {path}")


def _write_tag_only(opt, path, info, file_tags):
    """적용을 건너뛸 때(dirty 면) 태그만 갱신(원본 'Writing tag information')."""
    if (not opt.skip_tag) and info is not None and info.dirty:
        print(f"Writing tag information for {path}")
        _write_mp3gain_tag(path, info, file_tags,
                           save_timestamp=opt.save_time, use_id3=opt.use_id3)


def _do_apply(opt, path, steps, info, file_tags):
    """게인 적용 공통(원본 'Applying mp3 gain change of N to …' + 적용)."""
    print(f"Applying mp3 gain change of {steps} to {path}...")
    if opt.skip_tag:
        apply_gain(path, steps, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, steps, steps, info, file_tags,
                            wrap=opt.wrap_gain, save_timestamp=opt.save_time,
                            use_id3=opt.use_id3)


def _apply_track(opt, path, steps, max_sample, info, file_tags):
    """원본 main 의 applyTrack 적용 분기 동등(C-3 클립 포함).

    intGainChange==0: "No changes…" + dirty 면 "…but tag needs update" + 태그만.
    !=0: autoClip(-k) 하향 → 또는 -c 미지정 시 클립 조건 충족하면 stdin 질의 →
         goAhead 면 "Applying mp3 gain change of N to …" + 적용,
         아니면(질의 거부) 미적용 + dirty 면 태그만.
    """
    if steps == 0:
        print(f"No changes to {path} are necessary")
        if (not opt.skip_tag) and info is not None and info.dirty:
            print(f"...but tag needs update: Writing tag information for {path}")
            _write_mp3gain_tag(path, info, file_tags,
                               save_timestamp=opt.save_time, use_id3=opt.use_id3)
        return

    go_ahead = True
    if opt.auto_clip:
        original_steps = steps
        steps, clipped = _auto_clip_track(steps, max_sample)
        if clipped:
            print(f"Applying auto-clipped mp3 gain change of {steps} to {path}\n"
                  f"(Original suggested gain was {original_steps})")
    elif not opt.ignore_clip_warning:
        if max_sample * pow(2.0, steps / 4.0) > 32767.0:
            go_ahead = _query_user_for_clipping(path, steps)

    if go_ahead:
        _do_apply(opt, path, steps, info, file_tags)
    else:
        _write_tag_only(opt, path, info, file_tags)


def _apply_album_one(opt, path, steps, peak, info, file_tags):
    """원본 main 의 applyAlbum 적용 루프 한 곡 동등(C-3 곡별 클립 질의 포함).

    steps 는 이미 Album autoClip 하향이 반영된 단일 스텝(루프 밖에서 처리).
    intGainChange==0: "\nNo changes…"(앞 줄바꿈) + dirty 면 태그만.
    !=0: -c 미지정 시 곡별 클립(peak*2^(steps/4)>1.0) 충족하면 stdin 질의 →
         goAhead 면 적용, 아니면 dirty 면 태그만.
    """
    if steps == 0:
        print(f"\nNo changes to {path} are necessary")
        if (not opt.skip_tag) and info is not None and info.dirty:
            print(f"...but tag needs update: Writing tag information for {path}")
            _write_mp3gain_tag(path, info, file_tags,
                               save_timestamp=opt.save_time, use_id3=opt.use_id3)
        return

    go_ahead = True
    if not opt.ignore_clip_warning:
        if peak * pow(2.0, steps / 4.0) > 1.0:
            go_ahead = _query_user_for_clipping(path, steps)

    if go_ahead:
        _do_apply(opt, path, steps, info, file_tags)
    else:
        _write_tag_only(opt, path, info, file_tags)


def _run_analysis(opt, tags, album_recalc):
    """원본 main 의 분석 경로 동등(C-3 + D-2).

    tags: {path: (info, file_tags)} (선행 읽기 + recalc 비트마스크 반영 완료).
    album_recalc: 앨범 recalc 비트마스크(GetAlbumGain vs 태그 album 값 선택용).

    파일별로 분석해 Track 제안을 출력하고(또는 -r 면 적용), Album 조건이면 곡별
    결과를 모아 마지막에 Album 제안을 출력한다(또는 -a 면 적용). 클립(-k/-c stdin
    질의)은 적용 헬퍼가 처리한다. 마지막에 순수 분석 경로면 dirty 곡 태그를 기록.
    """
    rc = 0
    num_files = len(opt.files)
    # 원본 album 조건: argc-fileStart>1 && !applyTrack && !analysisTrack.
    do_album = (num_files > 1) and (not opt.apply_track) and (not opt.analysis_track)

    # (path, hist, peak, min_gain, max_gain, info, file_tags) — 분석 성공·샘플 충분
    album_results = []
    # 분석에 성공한(fileok) 모든 파일 — update file tags 블록용.
    ok_files = []

    for path in opt.files:
        info, file_tags = tags[path]

        if not opt.database_format:
            print(path)

        analyzed = _analyze_one(opt, path, info, file_tags)
        if analyzed is None:
            rc = 1
            continue

        hist, peak, min_gain, max_gain, raw_db, info, file_tags = analyzed
        max_sample = peak * 32768.0  # 출력 직전 원본 스케일로 환원

        if raw_db is NOT_ENOUGH_SAMPLES:
            print(f"{path} 에 분석할 샘플이 충분하지 않습니다", file=sys.stderr)
            rc = 1
            continue

        ok_files.append(path)

        db_change, steps = _quantize_steps(raw_db, opt)

        if opt.database_format:
            _print_track_database(opt, path, steps, db_change,
                                  max_sample, max_gain, min_gain)
        elif (not opt.apply_track) and (not opt.apply_album):
            _print_track_suggestion(opt, db_change, steps,
                                    max_sample, max_gain, min_gain)

        # Track 적용 (원본 applyTrack 분기, C-3 클립 포함).
        if opt.apply_track:
            _apply_track(opt, path, steps, max_sample, info, file_tags)

        if do_album:
            album_results.append(
                (path, hist, peak, min_gain, max_gain, info, file_tags))

    # Album 집계·제안·적용 (원본: numFiles>0 && !applyTrack && !analysisTrack)
    if do_album and album_results:
        # album dB: FULL recalc 면 누적 재계산, 아니면 첫 파일 태그 album/track 값.
        if opt.max_amp_only:
            album_db = 0.0
        elif album_recalc & FULL_RECALC:
            album_db = gain_from_histograms([r[1] for r in album_results])
        else:
            first_info = tags[opt.files[0]][0]
            if first_info.have_album_gain:
                album_db = first_info.album_gain
            else:
                album_db = first_info.track_gain

        if album_db is NOT_ENOUGH_SAMPLES:
            print("mp3 파일들에 분석할 샘플이 충분하지 않습니다", file=sys.stderr)
        else:
            max_max_sample = max(r[2] for r in album_results)
            max_max_gain = max(r[4] for r in album_results)
            min_min_gain = min(r[3] for r in album_results)

            # 전 곡 info 에 album 값 채우기 (원본 (!skipTag)&&(numFiles>1||applyAlbum)).
            if not opt.skip_tag:
                for path, _h, _p, _mn, _mx, info, _ft in album_results:
                    if info is not None:
                        _fill_album_info(info, album_db, max_max_sample,
                                         min_min_gain, max_max_gain)

            db_change, steps = _quantize_steps(album_db, opt)

            if opt.database_format:
                print(f'"Album"\t{steps}\t{db_change:f}\t'
                      f'{max_max_sample * 32768.0:f}\t{max_max_gain}\t{min_min_gain}')
                sys.stdout.flush()
            elif not opt.apply_album:
                _print_album_suggestion(opt, db_change, steps, album_results)

            # Album 적용 (원본 applyAlbum 분기: 전 곡 동일 스텝).
            if opt.apply_album:
                # Album autoClip 하향은 전 곡 루프 밖에서 한 번만(원본 /*MAA*/).
                if opt.auto_clip:
                    new_steps, clipped = _auto_clip_album(steps, max_max_sample)
                    if clipped:
                        print(f"Applying auto-clipped mp3 gain change of "
                              f"{new_steps} to album\n"
                              f"(Original suggested gain was {steps})")
                        steps = new_steps
                for path, _h, peak, _mn, _mx, info, file_tags in album_results:
                    _apply_album_one(opt, path, steps, peak, info, file_tags)

    # update file tags (원본 끝 블록): 순수 분석 경로에서만 dirty 곡 태그 기록.
    if (not opt.apply_track) and (not opt.apply_album) and \
            (not opt.direct_gain) and (not opt.direct_single_channel_gain) and \
            (not opt.delete_tag) and (not opt.skip_tag) and (not opt.check_tag_only):
        for path in ok_files:
            info, file_tags = tags[path]
            if info is not None and info.dirty:
                _write_mp3gain_tag(path, info, file_tags,
                                   save_timestamp=opt.save_time,
                                   use_id3=opt.use_id3)

    return rc


def _run_check_tag_only(opt):
    """원본 main 의 checkTagOnly 분기 동등(-s c).

    태그만 읽어 Track/Album 제안·peak·min/max 를 출력한다. 디코딩 없음.
    intGainChange/intAlbumGainChange 는 보정 없이 순수
    trackGain/(5*log10 2) round-half-away (db_to_steps 직접 사용).
    클립 경고는 원본 그대로 track_peak * 2^(steps/4) > 1.0 (Album 쪽도
    원본대로 track_peak 참조 — albumPeak 아님, 원본 동일 재현).
    출력 문구는 원본 영어 그대로, peak 는 출력 직전 ×32768 환원.
    """
    for path in opt.files:
        info, _file_tags = read_mp3gain_tags(path, opt.use_id3)
        if info is None:
            continue

        int_gain_change = db_to_steps(info.track_gain) if info.have_track_gain else 0
        int_album_gain_change = (
            db_to_steps(info.album_gain) if info.have_album_gain else 0
        )

        if not opt.database_format:
            print(path)
            if info.have_track_gain:
                print(f'Recommended "Track" dB change: {info.track_gain:f}')
                print(f'Recommended "Track" mp3 gain change: {int_gain_change}')
                if info.have_track_peak:
                    if info.track_peak * pow(2.0, int_gain_change / 4.0) > 1.0:
                        print("WARNING: some clipping may occur with this gain change!")
            if info.have_track_peak:
                print(f"Max PCM sample at current gain: {info.track_peak * 32768.0:f}")
            if info.have_min_max_gain:
                print(f"Max mp3 global gain field: {info.max_gain}")
                print(f"Min mp3 global gain field: {info.min_gain}")
            if info.have_album_gain:
                print(f'Recommended "Album" dB change: {info.album_gain:f}')
                print(f'Recommended "Album" mp3 gain change: {int_album_gain_change}')
                if info.have_track_peak:
                    if info.track_peak * pow(2.0, int_album_gain_change / 4.0) > 1.0:
                        print("WARNING: some clipping may occur with this gain change!")
            if info.have_album_peak:
                print(f"Max Album PCM sample at current gain: {info.album_peak * 32768.0:f}")
            if info.have_album_min_max_gain:
                print(f"Max Album mp3 global gain field: {info.album_max_gain}")
                print(f"Min Album mp3 global gain field: {info.album_min_gain}")
            print("")
        else:
            row = [path]
            if info.have_track_gain:
                row.append(str(int_gain_change))
                row.append(f"{info.track_gain:f}")
            else:
                row.append("NA")
                row.append("NA")
            if info.have_track_peak:
                row.append(f"{info.track_peak * 32768.0:f}")
            else:
                row.append("NA")
            if info.have_min_max_gain:
                row.append(str(info.max_gain))
                row.append(str(info.min_gain))
            else:
                row.append("NA")
                row.append("NA")
            if info.have_album_gain:
                row.append(str(int_album_gain_change))
                row.append(f"{info.album_gain:f}")
            else:
                row.append("NA")
                row.append("NA")
            if info.have_album_peak:
                row.append(f"{info.album_peak * 32768.0:f}")
            else:
                row.append("NA")
            if info.have_album_min_max_gain:
                row.append(str(info.album_max_gain))
                row.append(str(info.album_min_gain))
            else:
                row.append("NA")
                row.append("NA")
            print("\t".join(row))
            sys.stdout.flush()

    return 0


def _run_delete_tag(opt, path):
    """원본 main 의 deleteTag 분기 동등(-s d).

    태그를 읽지 않고(원본 read 단계 (!skipTag)&&(!deleteTag) 조건) 곧바로
    APE 태그를 제거하고, use_id3 면 ID3v2 태그도 제거한다.
    비-database 면 stderr 안내, database 면 NA 한 줄.
    """
    remove_mp3gain_ape_tag(path, opt.save_time)
    if opt.use_id3:
        from gaindb.id3 import remove_mp3gain_id3_tag
        remove_mp3gain_id3_tag(path, opt.save_time)

    if (not opt.quiet_mode) and (not opt.database_format):
        print(f"Deleting tag info of {path}...", file=sys.stderr)
    if opt.database_format:
        print(f"{path}\tNA\tNA\tNA\tNA\tNA")
    return 0


def main(argv):
    if len(argv) < 2:
        _err_usage()

    opt = parse_args(argv)

    if opt.database_format:
        _print_database_header(opt)

    if not opt.files:
        _err_usage()

    rc = 0

    # checkTagOnly / deleteTag 는 태그를 선행 읽지 않는다(원본 read 조건).
    if opt.check_tag_only:
        return _run_check_tag_only(opt)

    if opt.delete_tag:
        for path in opt.files:
            rc = _run_delete_tag(opt, path) or rc
        return rc

    # 그 외 경로(undo/직접게인/분석)는 전 파일 태그 선행 읽기 + recalc 계산(D-2).
    tags = _read_all_tags(opt)
    album_recalc = _compute_recalc(opt, tags)

    # 실행 분기 우선순위(원본 main 5.2).
    if opt.undo_changes:
        for path in opt.files:
            info, file_tags = tags[path]
            rc = _run_undo(opt, path, info, file_tags) or rc
        return rc

    if opt.direct_single_channel_gain:
        for path in opt.files:
            info, file_tags = tags[path]
            rc = _run_direct_single(opt, path, info, file_tags) or rc
        return rc

    if opt.direct_gain:
        for path in opt.files:
            info, file_tags = tags[path]
            rc = _run_direct(opt, path, info, file_tags) or rc
        return rc

    # 분석 경로(-r/-a/-e/-x/제안 출력/적용/클립) — C-1/C-2/C-3 + D-2 recalc 스킵.
    return _run_analysis(opt, tags, album_recalc)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
