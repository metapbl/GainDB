"""
mp3gain_cli.py - Gain dB 통합 CLI (원본 mp3gain 옵션 체계 재현)

원본 mp3gain.c 의 main() 옵션 파싱과 동등한 argv 순회 파서를 구현한다.
옵션 인식 규칙·인자 처리·실행 분기 우선순위를 원본 동작 그대로 따른다.

[묶음 A 범위]
- 옵션 파서 골격 (2글자 토큰 규칙, 인자=다음 토큰, fileStart 추적)
- 즉시 동작 옵션: -v(버전), -h/-?(도움말, ? wrap=wrap 설명),
  -q(quiet), -o(database 형식 + 헤더), -p(타임스탬프), -t/-T(temp)
- 나머지 옵션은 파싱만 해서 Options 에 저장(동작은 묶음 B~D 에서 연결)

[원본 동일 재현 합의 사항 (CLAUDE.md 5.4)]
- 붙여쓰기 인자 거부: 토큰이 정확히 2글자일 때만 옵션. 인자는 항상 다음 토큰.
  ('-d1.5' 같은 형태는 옵션으로 인식되지 않고 파일명으로 취급된다)
- -l joint stereo/mono 거부: 묶음 B 에서 적용
- -c 미지정 시 stdin y/n 클립 질의: 묶음 C 에서 적용

[배너 조정] 원본의 mpglib/저작권/프로그램명 배너는 기능 출력이 아니므로
Gain dB(ffmpeg 기반)에 맞게 조정한다. 기능 출력(-o, 분석 수치, 태그)은 원본 일치.
"""

import sys

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
            # 옵션이 아니면 더 이상 옵션 파싱 안 함(원본은 파일로 취급).
            # 원본은 루프를 계속 돌지만 2글자 아닌 토큰은 그냥 건너뛴다.
            # fileStart 는 옵션과 그 인자만큼만 증가하므로, 첫 비옵션부터 파일.
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


def main(argv):
    if len(argv) < 2:
        _err_usage()

    opt = parse_args(argv)

    if opt.database_format:
        _print_database_header(opt)

    # [묶음 A] 실행 분기는 아직 미연결. 파싱 결과를 확인용으로 요약 출력한다.
    # (묶음 B~D 에서 각 분기 동작을 채우며 이 요약은 제거 예정.)
    if not opt.quiet_mode:
        e = sys.stderr
        print("[묶음 A] 옵션 파싱 결과 (실행 분기는 후속 묶음에서 연결):", file=e)
        active = []
        if opt.apply_track: active.append("-r(track)")
        if opt.apply_album: active.append("-a(album)")
        if opt.analysis_track: active.append("-e")
        if opt.direct_gain: active.append(f"-g {opt.direct_gain_val}")
        if opt.direct_single_channel_gain:
            active.append(f"-l ch={opt.which_channel} {opt.direct_gain_val}")
        if opt.undo_changes: active.append("-u")
        if opt.check_tag_only: active.append("-s c")
        if opt.delete_tag: active.append("-s d")
        if opt.skip_tag: active.append("-s s")
        if opt.force_recalculate_tag: active.append("-s r")
        if opt.force_update_tag: active.append("-s u")
        if opt.use_id3: active.append("-s i(ID3v2)")
        if opt.auto_clip: active.append("-k")
        if opt.ignore_clip_warning: active.append("-c")
        if opt.max_amp_only: active.append("-x")
        if opt.reckless: active.append("-f")
        if opt.wrap_gain: active.append("-w")
        if opt.mp3_gain_mod: active.append(f"-m {opt.mp3_gain_mod}")
        if opt.db_gain_mod: active.append(f"-d {opt.db_gain_mod}")
        active.append(f"temp={'on' if opt.using_temp else 'off(-T)'}")
        active.append(f"save_time={opt.save_time}")
        active.append(f"db_format={opt.database_format}")
        print("  활성: " + (", ".join(active) if active else "(없음)"), file=e)
        print(f"  입력 파일 {len(opt.files)}개: {opt.files}", file=e)

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
