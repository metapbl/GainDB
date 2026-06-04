"""
mp3gain_cli.py - Gain dB 통합 CLI (원본 mp3gain 옵션 체계 재현)

원본 mp3gain.c 의 main() 옵션 파싱·실행 분기와 동등하게 구현한다.

[묶음 A] 옵션 파서 골격 + 즉시 동작 옵션(-v/-h/-?/-q/-o/-p/-t/-T).
[묶음 B] 직접 게인 실행 분기: -u(undo) / -l(단일 채널) / -g(전체 게인).
[묶음 C-1] 분석 경로 + 제안 출력(-r/-a/-e/-x/-m/-d/-o). 적용·클립 질의는
           C-2/C-3 에서 연결. 진행률 표시는 디코더 예외(ffmpeg 일괄 디코딩)의
           귀결로 생략한다(원본 기능 축소 아님 — 디코더 수단 차이의 부수 효과).

[원본 동일 재현 합의 사항 (CLAUDE.md 5.4)]
- 붙여쓰기 인자 거부: 토큰이 정확히 2글자일 때만 옵션. 인자는 항상 다음 토큰.
- -l joint stereo/mono 거부: writer.apply_gain 이 mode 1·3 거부(묶음 B 적용).
- -l whichChannel: 0=왼쪽, 그 외=오른쪽(원본 if(whichChannel) 동등).
- -c 미지정 시 stdin y/n 클립 질의: 묶음 C-3 에서 적용.

[실행 분기 우선순위 (원본 main 5.2)]
  checkTagOnly → undoChanges → directSingleChannelGain → directGain
  → deleteTag → 분석 경로. C-1 은 분석·제안 출력까지, 적용은 C-2.

[C-1 의 원본 정합 포인트]
- dBGainMod(-d)는 양자화 전 dB 에 더하고, mp3GainMod(-m)는 양자화 후 스텝에 더함.
- Track 클립 경고: maxsample * 2^(steps/4) > 32767.0.
- Album 곡별 클립 경고: trackPeak * 2^(steps/4) > 1.0 (단위 다름에 유의).
- maxAmpOnly(-x): dBchange=0 으로 두되 제안 출력 형식은 그대로.
- Album 조건: 파일 2개 이상 and not apply_track and not analysis_track.
- NOT_ENOUGH_SAMPLES: 해당 파일 stderr 메시지 후 제안·Album 집계에서 제외.

[배너 조정] mpglib/저작권/프로그램명 배너는 Gain dB(ffmpeg 기반)에 맞게 조정.
기능 출력(-o, 분석 수치, 태그)은 원본 일치.
"""

import sys
from math import pow

from gaindb.writer import apply_gain, scan_gain
from gaindb.tag import read_mp3gain_tags, change_gain_and_tag
from gaindb.decode import decode_pcm, DecodeError
from gaindb.analysis import (
    track_histogram,
    gain_from_histograms,
    track_peak,
    db_to_steps,
    NOT_ENOUGH_SAMPLES,
)

VERSION = "0.5.0-dev"
PROGNAME = "Gain dB"

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


def _read_tags(opt, path):
    """태그 읽기 골격(원본 main 의 전 파일 태그 선행 읽기 동등).

    skip_tag/delete_tag 면 읽지 않는다. force_recalculate_tag 의 분석값
    무효화는 분석 경로(묶음 D)에서 처리하므로 여기선 읽기만 한다.
    반환: (info, file_tags) 또는 (None, None).
    """
    if opt.skip_tag or opt.delete_tag:
        return None, None
    info, file_tags = read_mp3gain_tags(path, opt.use_id3)
    if opt.force_update_tag:
        info.dirty = True
    return info, file_tags


def _run_undo(opt, path):
    """원본 undoChanges 분기 동등.

    태그의 undo 정보로 역방향 게인을 적용한다. 원본은 directGain 을 켜서
    이중 태그 기록을 막지만, 우리는 change_gain_and_tag 가 한 번에 적용+기록.
    """
    info, file_tags = _read_tags(opt, path)
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


def _run_direct_single(opt, path):
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
        info, file_tags = _read_tags(opt, path)
        change_gain_and_tag(path, left, right, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("완료", file=sys.stderr)
    return 0


def _run_direct(opt, path):
    """원본 directGain 분기 동등(-g). 양 채널에 동일 게인."""
    val = opt.direct_gain_val
    if not opt.quiet_mode:
        print(f"게인 {val} 적용 중 -> {path} ...", file=sys.stderr)

    if opt.skip_tag:
        apply_gain(path, val, val, wrap=opt.wrap_gain)
    else:
        info, file_tags = _read_tags(opt, path)
        change_gain_and_tag(path, val, val, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("완료", file=sys.stderr)
    return 0


# ------------------------------------------------------------------
# [묶음 C-1] 분석 경로 + 제안 출력
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


def _analyze_one(opt, path):
    """한 곡을 분석해 (hist, peak, min_gain, max_gain, raw_db) 를 반환한다.

    원본은 한 디코딩 패스에서 라우드니스·peak·min/max gain 을 모두 뽑지만,
    여기서는 decode_pcm 으로 PCM 을 한 번 얻어 track_histogram·track_peak 를
    구하고, PCM 과 무관한 scan_gain(path) 로 min/max global_gain 을 구한다.

    maxAmpOnly(-x)면 라우드니스 히스토그램·게인 산출을 건너뛰고 hist=None,
    raw_db=0.0 으로 둔다(원본 maxAmpOnly 시 dBchange=0 동등).

    분석 불가(DecodeError)면 None 을 반환한다.
    """
    try:
        left, right, sample_rate = decode_pcm(path)
    except DecodeError as exc:
        print(f"{path} 분석 실패: {exc}", file=sys.stderr)
        return None

    peak = track_peak(left, right)
    min_gain, max_gain = scan_gain(path)
    if min_gain is None:
        min_gain = 0
    if max_gain is None:
        max_gain = 0

    if opt.max_amp_only:
        return (None, peak, min_gain, max_gain, 0.0)

    hist = track_histogram(left, right, sample_rate)
    raw = gain_from_histograms([hist])  # 단일 곡도 Album 경로와 코드 공유
    if raw is NOT_ENOUGH_SAMPLES:
        return (hist, peak, min_gain, max_gain, NOT_ENOUGH_SAMPLES)
    return (hist, peak, min_gain, max_gain, raw)


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

    results: (path, hist, peak, min_gain, max_gain) 의 리스트(분석 성공분).
    곡별 클립 경고는 trackPeak * 2^(steps/4) > 1.0 기준(원본과 동일 단위).
    """
    print("")
    print(f'Recommended "Album" dB change for all files: {db_change:f}')
    print(f'Recommended "Album" mp3 gain change for all files: {steps}')
    for path, _hist, peak, _min_g, _max_g in results:
        if peak * pow(2.0, steps / 4.0) > 1.0:
            print(f"WARNING: with this global gain change, "
                  f"some clipping may occur in file {path}")


def _run_analysis(opt):
    """원본 main 의 분석 경로 동등(C-1: 분석·제안 출력까지).

    파일별로 분석해 Track 제안을 출력하고, Album 조건이면 곡별 결과를 모아
    마지막에 Album 제안을 출력한다. 적용(-r/-a)·클립 질의는 C-2/C-3 에서.
    """
    rc = 0
    num_files = len(opt.files)
    # 원본 album 조건: argc-fileStart>1 && !applyTrack && !analysisTrack.
    do_album = (num_files > 1) and (not opt.apply_track) and (not opt.analysis_track)

    album_results = []  # (path, hist, peak, min_gain, max_gain) — 분석 성공·샘플 충분분

    for path in opt.files:
        if not opt.database_format:
            print(path)

        analyzed = _analyze_one(opt, path)
        if analyzed is None:
            rc = 1
            continue

        hist, peak, min_gain, max_gain, raw_db = analyzed
        max_sample = peak * 32768.0  # 출력 직전 원본 스케일로 환원

        if raw_db is NOT_ENOUGH_SAMPLES:
            print(f"{path} 에 분석할 샘플이 충분하지 않습니다", file=sys.stderr)
            rc = 1
            continue

        db_change, steps = _quantize_steps(raw_db, opt)

        if opt.database_format:
            _print_track_database(opt, path, steps, db_change,
                                  max_sample, max_gain, min_gain)
        elif (not opt.apply_track) and (not opt.apply_album):
            _print_track_suggestion(opt, db_change, steps,
                                    max_sample, max_gain, min_gain)

        if do_album:
            album_results.append((path, hist, peak, min_gain, max_gain))

    # Album 제안 (원본: numFiles>0 && !applyTrack && !analysisTrack)
    if do_album and album_results:
        if opt.max_amp_only:
            album_db = 0.0
        else:
            album_db = gain_from_histograms([r[1] for r in album_results])
        if album_db is NOT_ENOUGH_SAMPLES:
            print("mp3 파일들에 분석할 샘플이 충분하지 않습니다", file=sys.stderr)
        else:
            max_max_sample = max(r[2] for r in album_results)
            max_max_gain = max(r[4] for r in album_results)
            min_min_gain = min(r[3] for r in album_results)
            db_change, steps = _quantize_steps(album_db, opt)

            if opt.database_format:
                print(f'"Album"\t{steps}\t{db_change:f}\t'
                      f'{max_max_sample * 32768.0:f}\t{max_max_gain}\t{min_min_gain}')
                sys.stdout.flush()
            elif not opt.apply_album:
                _print_album_suggestion(opt, db_change, steps, album_results)

    # 적용 단계는 C-2 에서 연결.
    if (opt.apply_track or opt.apply_album) and not opt.quiet_mode:
        print("[미연결] -r/-a 적용 단계는 묶음 C-2 에서 구현 예정 "
              "(위 분석·제안 수치는 정상)", file=sys.stderr)

    return rc


def main(argv):
    if len(argv) < 2:
        _err_usage()

    opt = parse_args(argv)

    if opt.database_format:
        _print_database_header(opt)

    if not opt.files:
        _err_usage()

    # 실행 분기 우선순위(원본 main 5.2).
    # checkTagOnly / deleteTag 는 묶음 D 에서 연결.
    rc = 0

    # 직접 게인·undo 는 파일별 즉시 처리(묶음 B).
    if opt.check_tag_only:
        for path in opt.files:
            if not opt.quiet_mode:
                print(f"[미연결] -s c (태그 확인) 는 묶음 D 에서 구현 예정: {path}",
                      file=sys.stderr)
        return rc

    if opt.undo_changes:
        for path in opt.files:
            rc = _run_undo(opt, path) or rc
        return rc

    if opt.direct_single_channel_gain:
        for path in opt.files:
            rc = _run_direct_single(opt, path) or rc
        return rc

    if opt.direct_gain:
        for path in opt.files:
            rc = _run_direct(opt, path) or rc
        return rc

    if opt.delete_tag:
        for path in opt.files:
            if not opt.quiet_mode:
                print(f"[미연결] -s d (태그 삭제) 는 묶음 D 에서 구현 예정: {path}",
                      file=sys.stderr)
        return rc

    # 그 외: 분석 경로(-r/-a/-e/-x/제안 출력) — 묶음 C-1.
    return _run_analysis(opt)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
