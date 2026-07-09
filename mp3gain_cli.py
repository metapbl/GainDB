"""
mp3gain_cli.py - Gain dB unified CLI (re-implements the original mp3gain option scheme)

Mirrors the option parsing and execution branches of the original mp3gain.c main().

================================================================================
CLI I/O SPECIFICATION (user interface contract)
================================================================================
Invocation:
    python mp3gain_cli.py [options] <infile> [<infile 2> ...]

Option tokens (original mp3gain scheme; clean-room re-implementation):
    A token is an option ONLY if it is exactly two characters and begins with
    '-' or '/'. The option argument, when required, is ALWAYS the next token
    (glued arguments like "-g3" are rejected -- agreed exception, CLAUDE.md 5.4).

    -v            show version (to stderr) and exit 0
    -h / -? / -?w show usage / wrap explanation (to stderr) and exit
    -g <i>        apply gain i to both channels without analysis
    -l <c> <i>    apply gain i to one channel (c==0 left, else right); STEREO only
    -e            skip Album analysis even with multiple files
    -r            apply Track gain automatically
    -a            apply Album gain automatically (-r and -a together: -a wins)
    -k            auto-clip: lower Track/Album gain so no clipping occurs
    -m <i>        modify suggested mp3 gain by integer i (post-quantize)
    -d <n>        modify suggested dB gain by float n (pre-quantize)
    -c            ignore clipping warning (no stdin prompt)
    -o            database-friendly tab-delimited output (to stdout)
    -t            write via temp file then replace original (default)
    -T            modify the original file directly
    -q            quiet: no status messages (stderr)
    -p            preserve original file timestamp
    -x            only find max amplitude (no loudness analysis)
    -f            assume MPEG 2 Layer III (skip Layer I/II mis-name check)
    -s c          check stored tag info only (no other processing)
    -s d          delete stored tag info (no other processing)
    -s s          skip (ignore) stored tag info
    -s r          force re-calculation (does not read tag info)
    -s u          force update (mark tags dirty so they are rewritten)
    -s i          use ID3v2 tag for gain info
    -s a          use APE tag for gain info (default)
    -u            undo changes (based on stored tag info)
    -w            "wrap" gain change if gain+change > 255 or < 0

Debug sub-commands (NOT part of the original mp3gain scheme -- Gain dB dev tools,
agreed in CLAUDE.md D-3; absorbed from former scan_gain.py / inspect_tag.py):
    --debug-scan <file> [...]   dump frame parse + global_gain min/max
    --debug-tag  <file> [...]   dump APEv2 tag structure + recognized gain fields
    These are intercepted before the 2-char option parser; their output is
    developer-oriented (English) and is not an original-mp3gain reproduction.

Output channels:
    stdout - functional output reproduced from the original: per-track/album
             suggestions, database rows, "Applying mp3 gain change...",
             "No changes...", clipping WARNING lines. These strings match the
             original mp3gain English verbatim.
    stderr - banner / usage / version / status messages ("Undoing...",
             "Applying gain change of N to CHANNEL...", "done", "Deleting tag
             info...", clip prompt). Original-derived strings are verbatim;
             a few are Gain-dB-specific English (e.g. ffmpeg decode failure).

Exit code:
    main() returns an int that becomes the process exit code: 0 on success,
    non-zero (1) if any file failed (rc accumulates per file). Usage/version
    paths call sys.exit() directly.

Localization note (CLAUDE.md agreed): the CLI emits English ONLY. Korean/English
localization is the responsibility of the future GUI layer (step 6), not the CLI.
================================================================================

[Bundle A] Option parser skeleton + immediate options (-v/-h/-?/-q/-o/-p/-t/-T).
[Bundle B] Direct gain branches: -u(undo) / -l(single channel) / -g(full gain).
[Bundle C-1] Analysis path + suggestion output (-r/-a/-e/-x/-m/-d/-o).
[Bundle C-2] -r(Track apply)/-a(Album apply) wiring (single decode pass).
[Bundle C-3] Clip handling: -k(autoClip) + stdin y/n query when -c absent.
[Bundle D-1] -s c(checkTagOnly) + -s d(deleteTag).
[Bundle D-2] -s r/-s u + recalc bitmask decode-skip + "update file tags" block.
[Bundle D-3] Absorbed dev CLIs as --debug-scan/--debug-tag; full English output.
"""

import sys
from math import pow, log10, floor

from gaindb.frame import parse_file
from gaindb.writer import apply_gain, scan_gain
from gaindb.tag import (
    read_mp3gain_tags,
    read_mp3gain_ape_tag,
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

# Original recalc bitmask (mp3gain.c).
FULL_RECALC = 1
AMP_RECALC = 2
MIN_MAX_GAIN_RECALC = 4

# Original SWITCH_CHAR: Windows accepts both '/' and '-', elsewhere just '-'.
# We accept both as option prefixes (matches the original WIN32 branch).
_SWITCH_CHARS = ("-", "/")


class Options:
    """Parsed global options. 1:1 with the original main()'s global flags."""

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
        # gain modes
        self.apply_track = False           # -r
        self.apply_album = False           # -a
        self.analysis_track = False        # -e
        # clipping
        self.ignore_clip_warning = False   # -c
        self.auto_clip = False             # -k
        # direct gain
        self.direct_gain = False           # -g
        self.direct_single_channel_gain = False  # -l
        self.direct_gain_val = 0
        self.which_channel = 0
        # gain modifiers
        self.mp3_gain_mod = 0              # -m
        self.db_gain_mod = 0.0             # -d
        # output / behaviour flags
        self.database_format = False       # -o
        self.using_temp = True             # -t (default) / -T
        self.quiet_mode = False            # -q
        self.save_time = False             # -p
        self.max_amp_only = False          # -x
        self.reckless = False              # -f
        self.wrap_gain = False             # -w
        self.undo_changes = False          # -u
        # tag modes (-s ...)
        self.skip_tag = False              # -s s
        self.delete_tag = False            # -s d
        self.force_recalculate_tag = False  # -s r
        self.force_update_tag = False      # -s u
        self.check_tag_only = False        # -s c
        self.use_id3 = False               # -s i / -s a
        # input files
        self.files = []
        self.file_start = 1


def _show_version(out=sys.stderr):
    # Original showVersion: "%s version %s". The ffmpeg note is Gain-dB-specific.
    print(f"{PROGNAME} version {VERSION}", file=out)
    print("PCM decoding via ffmpeg (called from PATH)", file=out)


def _err_usage():
    """Equivalent of the original errUsage: short usage + exit 1.

    Copyright line is kept verbatim (attribution to the original author). The
    mpglib line is replaced because Gain dB decodes via ffmpeg, not mpglib.
    """
    _show_version()
    print("copyright(c) 2001-2009 by Glen Sawyer", file=sys.stderr)
    print("Gain dB is a clean-room re-implementation; PCM decoding uses ffmpeg",
          file=sys.stderr)
    print(f"Usage: {PROGNAME} [options] <infile> [<infile 2> ...]", file=sys.stderr)
    print("  --use -? or -h for a full list of options", file=sys.stderr)
    sys.exit(1)


def _wrap_explanation():
    """Equivalent of the original wrapExplanation (verbatim English) + exit."""
    e = sys.stderr
    print("Here's the problem:", file=e)
    print('The "global gain" field that mp3gain adjusts is an 8-bit unsigned '
          "integer, so", file=e)
    print("the possible values are 0 to 255.", file=e)
    print("", file=e)
    print("MOST mp3 files (in fact, ALL the mp3 files I've examined so far) "
          "don't go", file=e)
    print("over 230. So there's plenty of headroom on top-- you can increase "
          "the gain", file=e)
    print("by 37dB (multiplying the amplitude by 76) without a problem.", file=e)
    print("", file=e)
    print("The problem is at the bottom of the range. Some encoders create "
          "frames with", file=e)
    print("0 as the global gain for silent frames.", file=e)
    print("What happens when you _lower_ the global gain by 1?", file=e)
    print("Well, in the past, mp3gain always simply wrapped the result up to 255.",
          file=e)
    print("That way, if you lowered the gain by any amount and then raised it "
          "by the", file=e)
    print("same amount, the mp3 would always be _exactly_ the same.", file=e)
    print("", file=e)
    print("There are a few encoders out there, unfortunately, that create "
          "0-gain frames", file=e)
    print("with other audio data in the frame.", file=e)
    print("As long as the global gain is 0, you'll never hear the data.", file=e)
    print("But if you lower the gain on such a file, the global gain is "
          "suddenly _huge_.", file=e)
    print("If you play this modified file, there might be a brief, very loud blip.",
          file=e)
    print("", file=e)
    print("So now the default behavior of mp3gain is to _not_ wrap gain changes.",
          file=e)
    print("In other words,", file=e)
    print("1) If the gain change would make a frame's global gain drop below 0,",
          file=e)
    print("   then the global gain is set to 0.", file=e)
    print("2) If the gain change would make a frame's global gain grow above 255,",
          file=e)
    print("   then the global gain is set to 255.", file=e)
    print("3) If a frame's global gain field is already 0, it is not changed, "
          "even if", file=e)
    print("   the gain change is a positive number", file=e)
    print("", file=e)
    print('To use the original "wrapping" behavior, use the "-w" switch.', file=e)
    sys.exit(0)


def _full_usage():
    """Equivalent of the original fullUsage (verbatim English) + exit.

    Note: the original fullUsage omits the "-s u" line (present in code, missing
    in help). We add it here as an agreed correction of the original's omission
    (CLAUDE.md D-3).
    """
    _show_version()
    e = sys.stderr
    print("copyright(c) 2001-2009 by Glen Sawyer", file=e)
    print("Gain dB is a clean-room re-implementation; PCM decoding uses ffmpeg",
          file=e)
    print(f"Usage: {PROGNAME} [options] <infile> [<infile 2> ...]", file=e)
    print("options:", file=e)
    print("\t-v - show version number", file=e)
    print("\t-g <i>  - apply gain i without doing any analysis", file=e)
    print("\t-l 0 <i> - apply gain i to channel 0 (left channel)", file=e)
    print("\t          without doing any analysis (ONLY works for STEREO files,",
          file=e)
    print("\t          not Joint Stereo)", file=e)
    print("\t-l 1 <i> - apply gain i to channel 1 (right channel)", file=e)
    print("\t-e - skip Album analysis, even if multiple files listed", file=e)
    print("\t-r - apply Track gain automatically (all files set to equal loudness)",
          file=e)
    print("\t-k - automatically lower Track/Album gain to not clip audio", file=e)
    print("\t-a - apply Album gain automatically (files are all from the same",
          file=e)
    print("\t              album: a single gain change is applied to all files, so",
          file=e)
    print("\t              their loudness relative to each other remains unchanged,",
          file=e)
    print("\t              but the average album loudness is normalized)", file=e)
    print("\t-m <i> - modify suggested MP3 gain by integer i", file=e)
    print("\t-d <n> - modify suggested dB gain by floating-point n", file=e)
    print("\t-c - ignore clipping warning when applying gain", file=e)
    print("\t-o - output is a database-friendly tab-delimited list", file=e)
    print("\t-t - write modified mp3 to temp file, then delete original", file=e)
    print("\t     instead of modifying bytes in original file (default)", file=e)
    print("\t-T - directly modify mp3 file (opposite of -t)", file=e)
    print("\t-q - Quiet mode: no status messages", file=e)
    print("\t-p - Preserve original file timestamp", file=e)
    print("\t-x - Only find max. amplitude of file", file=e)
    print("\t-f - Assume input file is an MPEG 2 Layer III file", file=e)
    print("\t     (i.e. don't check for mis-named Layer I or Layer II files)",
          file=e)
    print("\t-? or -h - show this message", file=e)
    print("\t-s c - only check stored tag info (no other processing)", file=e)
    print("\t-s d - delete stored tag info (no other processing)", file=e)
    print("\t-s s - skip (ignore) stored tag info (do not read or write tags)",
          file=e)
    print("\t-s r - force re-calculation (do not read tag info)", file=e)
    print("\t-s u - force update (mark tags dirty so they are rewritten)", file=e)
    print("\t-s i - use ID3v2 tag for MP3 gain info", file=e)
    print("\t-s a - use APE tag for MP3 gain info (default)", file=e)
    print("\t-u - undo changes made (based on stored tag info)", file=e)
    print('\t-w - "wrap" gain change if gain+change > 255 or gain+change < 0',
          file=e)
    print('\t      (use "-? wrap" switch for a complete explanation)', file=e)
    print("If you specify -r and -a, only the second one will work", file=e)
    print("If you do not specify -c, the program will stop and ask before", file=e)
    print("     applying gain change to a file that might clip", file=e)
    sys.exit(0)


def _atof(s):
    try:
        return float(s)
    except ValueError:
        return 0.0


def _atoi(s):
    # Original atoi: take the leading integer, 0 on failure. Minimal re-impl.
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
    """Fetch the next token as the argument. errUsage (exit) if missing."""
    if i + 1 < len(argv):
        return argv[i + 1], i + 1
    _err_usage()


def parse_args(argv):
    """Equivalent of the original main()'s option parsing loop. Returns Options.

    argv is the full list including the program name (argv[0] is ignored).
    """
    opt = Options()
    file_start = 1
    i = 1
    n = len(argv)

    while i < n:
        tok = argv[i]
        # Option recognition: prefix '-' or '/' and length exactly 2.
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
            # '-? wrap' or '-h wrap' -> wrap explanation. Otherwise -> full help.
            if i + 1 < n and argv[i + 1][:1].lower() == "w":
                _wrap_explanation()
            _full_usage()
        elif c == "k":
            opt.auto_clip = True
        elif c == "l":
            opt.direct_single_channel_gain = True
            opt.direct_gain = False
            # Two arguments: channel, gain value (both as following tokens).
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
        elif tok[1] == "t":   # lowercase t: use temp file
            opt.using_temp = True
        elif tok[1] == "T":   # uppercase T: modify directly
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
            # Original: an unrecognized option only warns and continues.
            print(f"I don't recognize option {tok}", file=sys.stderr)

        i += 1

    opt.file_start = file_start
    opt.files = argv[file_start:]
    return opt


def _print_database_header(opt):
    """Equivalent of the original main()'s three -o header branches."""
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
    """Equivalent of the original forceRecalculateTag handling.

    For each present album/track gain/peak/minmax field, set dirty and clear it.
    Undo information is preserved (original comment "NOT Undo information!").
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
    """Equivalent of the original main()'s 'read all tags first' phase.

    Pre-reads each file's (info, file_tags) (needed for the recalc bitmask and
    per-file skip decisions). Original order:
      - initialize dirty to forceUpdateTag (before reading).
      - only read when (not skip_tag and not delete_tag); otherwise empty info.
      - if forceRecalculateTag, _clear_for_recalc after reading.

    Returns: {path: (info, file_tags)}.
    """
    from gaindb.tag import MP3GainTagInfo, FileTags

    tags = {}
    for path in opt.files:
        if opt.skip_tag or opt.delete_tag:
            # Don't read the tag. Empty info (calloc equivalent), dirty=force_update.
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
    """Equivalent of the original main()'s recalc bitmask computation.

    album_recalc = (force_recalc or skip_tag) ? FULL : 0.
    When (not skip_tag and not delete_tag and not force_recalc), check whether the
    already-stored info is sufficient: set bits on each file's info.recalc (track
    side) and album_recalc (album side). Album checks only when 'more than one
    file and not apply_track and not analysis_track'. curAlbum* comparison uses
    exact float equality (!=), matching the original (no epsilon). Finally each
    file's info.recalc |= album_recalc.

    Returns: album_recalc (already OR'd into every file's info.recalc).
    """
    files = opt.files
    multi = len(files) > 1
    album_check = multi and (not opt.apply_track) and (not opt.analysis_track)

    album_recalc = FULL_RECALC if (opt.force_recalculate_tag or opt.skip_tag) else 0

    if (not opt.skip_tag) and (not opt.delete_tag) and (not opt.force_recalculate_tag):
        # Based on the first file's album values (original: tagInfo[fileStart].album*).
        first_info = tags[files[0]][0]
        cur_album_gain = first_info.album_gain
        cur_album_peak = first_info.album_peak
        cur_album_min = first_info.album_min_gain
        cur_album_max = first_info.album_max_gain

        for path in files:
            info = tags[path][0]
            if not opt.max_amp_only:
                # gain-related checks (skipped under maxAmpOnly).
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

    # Propagate album recalc to each file (original: tagInfo[].recalc |= albumRecalc).
    for path in files:
        tags[path][0].recalc |= album_recalc

    return album_recalc


# ------------------------------------------------------------------
# [Bundle B] Direct gain / undo
# ------------------------------------------------------------------

def _run_undo(opt, path, info, file_tags):
    """Equivalent of the original undoChanges branch.

    Applies the reverse gain from the tag's undo info. The original sets
    directGain to avoid double tag-writes; here change_gain_and_tag applies+writes
    in one go.
    """
    have_undo = info is not None and info.have_undo
    nonzero = have_undo and (info.undo_left or info.undo_right)

    if nonzero:
        if (not opt.quiet_mode) and (not opt.database_format):
            print(f"Undoing mp3gain changes ({info.undo_left},{info.undo_right}) "
                  f"to {path}...", file=sys.stderr)
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
                print(f"No changes to undo in {path}", file=sys.stderr)
            else:
                print(f"No undo information in {path}", file=sys.stderr)
        return 1


def _run_direct_single(opt, path, info, file_tags):
    """Equivalent of the original directSingleChannelGain branch (-l).

    whichChannel: 0 == left, else right. STEREO/dual only (writer rejects joint
    stereo / mono).
    """
    val = opt.direct_gain_val
    if not opt.quiet_mode:
        print(f"Applying gain change of {val} to CHANNEL {opt.which_channel} "
              f"of {path}...", file=sys.stderr)

    if opt.which_channel:   # non-zero -> right
        left, right = 0, val
    else:                   # zero -> left
        left, right = val, 0

    if opt.skip_tag:
        apply_gain(path, left, right, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, left, right, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("\ndone", file=sys.stderr)
    return 0


def _run_direct(opt, path, info, file_tags):
    """Equivalent of the original directGain branch (-g). Same gain on both channels."""
    val = opt.direct_gain_val
    if not opt.quiet_mode:
        print(f"Applying gain change of {val} to {path}...", file=sys.stderr)

    if opt.skip_tag:
        apply_gain(path, val, val, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, val, val, info, file_tags,
                            wrap=opt.wrap_gain, use_id3=opt.use_id3)

    if not opt.quiet_mode:
        print("\ndone", file=sys.stderr)
    return 0


# ------------------------------------------------------------------
# [Bundle C-1/C-2/C-3] Analysis path + suggestions + apply + clip
# ------------------------------------------------------------------

def _quantize_steps(db_change, opt):
    """Equivalent of the original main()'s dB->step quantize order.

    dBGainMod(-d) is added to dB BEFORE quantize; db_to_steps quantizes; then
    mp3GainMod(-m) is added to the step count. Returns: (modified dBchange, steps).
    """
    db_change += opt.db_gain_mod
    steps = db_to_steps(db_change)
    steps += opt.mp3_gain_mod
    return db_change, steps


def _query_user_for_clipping(path, steps):
    """Equivalent of the original queryUserForClipping (stdin y/n prompt).

    Prints the WARNING line, then repeatedly asks "Make change? [y/n]:". First
    letter Y -> True, N -> False. EOF -> N (False). The original reads char by
    char via getchar(); we reproduce via the first char of an input() line.
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
            return False  # original: EOF -> 'N'
        ch = line[:1].upper()
        if ch == "Y":
            return True
        if ch == "N":
            return False
        # Not Y/N -> ask again (matches the original while loop).


def _auto_clip_track(steps, max_sample):
    """Equivalent of the original Track autoClip.

    intMaxNoClipGain = floor(4*log10(32767/maxsample)/log10(2)). If the suggested
    steps exceed this, lower it. Returns (new steps, True) if lowered, else
    (original steps, False).
    """
    if max_sample <= 0:
        return steps, False
    max_no_clip = int(floor(4.0 * log10(32767.0 / max_sample) / log10(2.0)))
    if steps > max_no_clip:
        return max_no_clip, True
    return steps, False


def _auto_clip_album(steps, max_max_sample):
    """Equivalent of the original Album autoClip.

    intMaxNoClipGain = floor(-4*log10(maxmaxsample)/log10(2)) (maxmaxsample is the
    normalized album peak). If suggested steps exceed it, lower. Called once,
    outside the per-file loop. Returns (new steps, True) if lowered, else
    (original steps, False).
    """
    if max_max_sample <= 0:
        return steps, False
    max_no_clip = int(floor(-4.0 * log10(max_max_sample) / log10(2.0)))
    if steps > max_no_clip:
        return max_no_clip, True
    return steps, False


def _analyze_one(opt, path, info, file_tags):
    """Analyze one track, returning analysis values + tag (info/file_tags).

    Skips decode (ffmpeg) / scan_gain per info.recalc bits (D-2, the consequence
    of the ffmpeg decoder exception -- CLAUDE.md 1.1/7). Resulting numbers match
    the original.

    Returns: (hist, peak, min_gain, max_gain, raw_db, info, file_tags)
      - hist: loudness histogram (None unless FULL recalc).
      - peak: normalized peak (0..1, can exceed 1.0).
      - min_gain, max_gain: frame global_gain min/max.
      - raw_db: 89dB-referenced Track dB. 0.0 under maxAmpOnly, tag value if not
                FULL, NOT_ENOUGH_SAMPLES on insufficient samples.

    Returns None when analysis is impossible (DecodeError).
    """
    recalc = info.recalc if info is not None else FULL_RECALC
    need_decode = bool(recalc & (FULL_RECALC | AMP_RECALC))
    # min/max global_gain is a frame-side value (no decoding needed). The original
    # scanFrameGain runs on ANY recalc path (FULL/AMP/MIN_MAX), so min/max is
    # always produced whenever any recalc is requested -- e.g. under -s s (FULL
    # only) or -x (AMP only). Binding it to MIN_MAX_GAIN_RECALC alone dropped
    # min/max to 0/0 in those cases; widen to match the original.
    need_scan = bool(recalc & (FULL_RECALC | AMP_RECALC | MIN_MAX_GAIN_RECALC))

    # --- peak: ffmpeg result if decoding, else tag value ---
    left = right = sample_rate = None
    if need_decode:
        try:
            left, right, sample_rate = decode_pcm(path)
        except DecodeError as exc:
            print(f"Failed to analyze {path}: {exc}", file=sys.stderr)
            return None
        peak = track_peak(left, right)
    else:
        peak = info.track_peak if (info is not None and info.have_track_peak) else 0.0

    # --- min/max global_gain: scan_gain if scanning, else tag value ---
    if need_scan:
        min_gain, max_gain = scan_gain(path)
        if min_gain is None:
            min_gain = 0
        if max_gain is None:
            max_gain = 0
    else:
        min_gain = info.min_gain if (info is not None and info.have_min_max_gain) else 0
        max_gain = info.max_gain if (info is not None and info.have_min_max_gain) else 0

    # --- maxAmpOnly: no dB analysis ---
    if opt.max_amp_only:
        return (None, peak, min_gain, max_gain, 0.0, info, file_tags)

    # --- raw_db: compute loudness if FULL, else tag track_gain ---
    if recalc & FULL_RECALC:
        hist = track_histogram(left, right, sample_rate)
        raw = gain_from_histograms([hist])  # single track shares the Album path
        if raw is NOT_ENOUGH_SAMPLES:
            return (hist, peak, min_gain, max_gain, NOT_ENOUGH_SAMPLES,
                    info, file_tags)
    else:
        hist = None
        raw = info.track_gain if (info is not None and info.have_track_gain) else 0.0

    # Analysis success -> fill 89dB-referenced track values (original curTag update).
    if info is not None:
        _fill_track_info(info, raw, peak, min_gain, max_gain)

    return (hist, peak, min_gain, max_gain, raw, info, file_tags)


def _print_track_suggestion(opt, db_change, steps, max_sample, max_gain, min_gain):
    """Equivalent of the original non-database Track suggestion (stdout, %f=6dp)."""
    print(f'Recommended "Track" dB change: {db_change:f}')
    print(f'Recommended "Track" mp3 gain change: {steps}')
    if max_sample * pow(2.0, steps / 4.0) > 32767.0:
        print("WARNING: some clipping may occur with this gain change!")
    print(f"Max PCM sample at current gain: {max_sample:f}")
    print(f"Max mp3 global gain field: {max_gain}")
    print(f"Min mp3 global gain field: {min_gain}")
    print("")


def _print_track_database(opt, path, steps, db_change, max_sample, max_gain, min_gain):
    """Equivalent of the original database Track row."""
    print(f"{path}\t{steps}\t{db_change:f}\t{max_sample:f}\t{max_gain}\t{min_gain}")
    sys.stdout.flush()


def _print_album_suggestion(opt, db_change, steps, results):
    """Equivalent of the original non-database Album suggestion.

    results: list of (path, hist, peak, min_gain, max_gain, info, file_tags).
    Per-file clip warning uses trackPeak * 2^(steps/4) > 1.0 (original unit).
    """
    print("")
    print(f'Recommended "Album" dB change for all files: {db_change:f}')
    print(f'Recommended "Album" mp3 gain change for all files: {steps}')
    for path, _hist, peak, _min_g, _max_g, _info, _ft in results:
        if peak * pow(2.0, steps / 4.0) > 1.0:
            print(f"WARNING: with this global gain change, "
                  f"some clipping may occur in file {path}")


def _write_tag_only(opt, path, info, file_tags):
    """When skipping the apply (but dirty), write only the tag (original 'Writing tag information')."""
    if (not opt.skip_tag) and info is not None and info.dirty:
        print(f"Writing tag information for {path}")
        _write_mp3gain_tag(path, info, file_tags,
                           save_timestamp=opt.save_time, use_id3=opt.use_id3)


def _do_apply(opt, path, steps, info, file_tags):
    """Common gain apply (original 'Applying mp3 gain change of N to ...' + apply)."""
    print(f"Applying mp3 gain change of {steps} to {path}...")
    if opt.skip_tag:
        apply_gain(path, steps, wrap=opt.wrap_gain)
    else:
        change_gain_and_tag(path, steps, steps, info, file_tags,
                            wrap=opt.wrap_gain, save_timestamp=opt.save_time,
                            use_id3=opt.use_id3)


def _apply_track(opt, path, steps, max_sample, info, file_tags):
    """Equivalent of the original main()'s applyTrack apply branch (incl. C-3 clip).

    intGainChange==0: "No changes..." + if dirty "...but tag needs update" + tag only.
    !=0: autoClip(-k) lowers -> or if -c absent and clip condition holds, stdin
         prompt -> if goAhead "Applying mp3 gain change of N to ..." + apply,
         else (prompt declined) no apply + tag only if dirty.
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
    """Equivalent of the original main()'s applyAlbum per-file loop (incl. C-3 clip).

    steps already reflects the Album autoClip lowering (handled outside the loop).
    intGainChange==0: "\nNo changes..." (leading newline) + tag only if dirty.
    !=0: if -c absent and per-file clip (peak*2^(steps/4)>1.0) holds, stdin prompt
         -> if goAhead apply, else tag only if dirty.
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
    """Equivalent of the original main()'s analysis path (C-3 + D-2).

    tags: {path: (info, file_tags)} (pre-read + recalc bitmask applied).
    album_recalc: album recalc bitmask (GetAlbumGain vs tag album value).

    Per file: analyze, print Track suggestion (or apply if -r); if the album
    condition holds, collect per-file results and print the Album suggestion at
    the end (or apply if -a). Clipping (-k / -c stdin prompt) is handled by the
    apply helpers. Finally, for a pure analysis path, write dirty file tags.
    """
    rc = 0
    num_files = len(opt.files)
    # Original album condition: argc-fileStart>1 && !applyTrack && !analysisTrack.
    do_album = (num_files > 1) and (not opt.apply_track) and (not opt.analysis_track)

    # (path, hist, peak, min_gain, max_gain, info, file_tags) -- analyzed & enough samples
    album_results = []
    # All files that analyzed OK (fileok) -- for the update file tags block.
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
        max_sample = peak * 32768.0  # back to original scale just before output

        if raw_db is NOT_ENOUGH_SAMPLES:
            print(f"Not enough samples in {path} to do analysis", file=sys.stderr)
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

        # Track apply (original applyTrack branch, C-3 clip included).
        if opt.apply_track:
            _apply_track(opt, path, steps, max_sample, info, file_tags)

        if do_album:
            album_results.append(
                (path, hist, peak, min_gain, max_gain, info, file_tags))

    # Album aggregate / suggest / apply (original: numFiles>0 && !applyTrack && !analysisTrack)
    if do_album and album_results:
        # album dB: recompute if FULL recalc, else first file's tag album/track value.
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
            print("Not enough samples in mp3 files to do analysis", file=sys.stderr)
        else:
            max_max_sample = max(r[2] for r in album_results)
            max_max_gain = max(r[4] for r in album_results)
            min_min_gain = min(r[3] for r in album_results)

            # Fill album values into every file's info (original (!skipTag)&&(numFiles>1||applyAlbum)).
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

            # Album apply (original applyAlbum branch: same step for all files).
            if opt.apply_album:
                # Album autoClip lowering happens once, outside the loop (original /*MAA*/).
                if opt.auto_clip:
                    new_steps, clipped = _auto_clip_album(steps, max_max_sample)
                    if clipped:
                        print(f"Applying auto-clipped mp3 gain change of "
                              f"{new_steps} to album\n"
                              f"(Original suggested gain was {steps})")
                        steps = new_steps
                for path, _h, peak, _mn, _mx, info, file_tags in album_results:
                    _apply_album_one(opt, path, steps, peak, info, file_tags)

    # update file tags (original end block): only on a pure analysis path, write dirty tags.
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
    """Equivalent of the original main()'s checkTagOnly branch (-s c).

    Reads tags only, prints Track/Album suggestions / peak / min/max. No decoding.
    intGainChange / intAlbumGainChange are the unmodified
    trackGain/(5*log10 2) round-half-away (db_to_steps directly). The clip warning
    uses, as in the original, track_peak * 2^(steps/4) > 1.0 (Album side also
    references track_peak -- not albumPeak; faithful original reproduction).
    Strings are the original English verbatim; peak is x32768 just before output.
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
    """Equivalent of the original main()'s deleteTag branch (-s d).

    Without reading the tag (original read step (!skipTag)&&(!deleteTag)), removes
    the APE tag, and the ID3v2 tag too when use_id3. Non-database prints to stderr;
    database prints an NA row.
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


# ------------------------------------------------------------------
# [Bundle D-3] Absorbed developer diagnostic sub-commands
# ------------------------------------------------------------------

def _run_debug_scan(files):
    """Developer diagnostic (absorbed from scan_gain.py). NOT original mp3gain.

    Parses frames and dumps format, frame count, global_gain min/max, and the
    first few frames' gains. English output for dev inspection.
    """
    rc = 0
    for path in files:
        frame_count = 0
        min_gain = 256
        max_gain = -1
        first_samples = []
        first_header = None

        for frame in parse_file(path):
            if first_header is None:
                first_header = frame
            frame_count += 1
            for g in frame.gains:
                if g < min_gain:
                    min_gain = g
                if g > max_gain:
                    max_gain = g
            if len(first_samples) < 8:
                first_samples.append((frame.offset, frame.gains))

        if frame_count == 0:
            print(f"No valid MP3 frames found in {path}", file=sys.stderr)
            rc = 1
            continue

        ver_name = {3: "MPEG1", 2: "MPEG2", 0: "MPEG2.5"}.get(
            first_header.mpegver, "?")
        print(f"file            : {path}")
        print(f"format          : {ver_name}, {first_header.samplerate_hz} Hz, "
              f"{first_header.bitrate_kbps} kbps, "
              f"{'mono' if first_header.nchan == 1 else 'stereo'}, "
              f"CRC={'yes' if first_header.has_crc else 'no'}")
        print(f"frame count     : {frame_count}")
        print(f"min global_gain : {min_gain}")
        print(f"max global_gain : {max_gain}")
        print("first frames' global_gain:")
        for off, gains in first_samples:
            print(f"  offset {off}: {gains}")
        print("")
    return rc


def _run_debug_tag(files):
    """Developer diagnostic (absorbed from inspect_tag.py). NOT original mp3gain.

    Calls read_mp3gain_ape_tag and dumps the parsed APE tag structure (tag offset,
    tail-tag detection, recognized gain fields). English output for dev inspection.
    """
    import os

    rc = 0
    for path in files:
        try:
            file_size = os.path.getsize(path)
        except OSError as exc:
            print(f"Can't stat {path}: {exc}", file=sys.stderr)
            rc = 1
            continue

        info, ft = read_mp3gain_ape_tag(path)

        print(f"=== {path} ===")
        print(f"file_size        : {file_size}")
        print(f"tag_offset       : {ft.tag_offset}"
              f"  (audio body ends here; {file_size - ft.tag_offset} tail bytes)")

        if ft.ape_tag is not None:
            ape = ft.ape_tag
            print(f"APE tag          : yes  "
                  f"(have_header={ape.have_header}, "
                  f"original_tag_size={ape.original_tag_size}, "
                  f"other_fields_size={ape.other_fields_size})")
        else:
            print("APE tag          : none")

        if ft.lyrics3_tag is not None:
            print(f"Lyrics3v2 tag    : yes  (size={ft.lyrics3_tag_size})")
        else:
            print("Lyrics3v2 tag    : none")

        if ft.id3v1_tag is not None:
            print("ID3v1 tag        : yes  (128 bytes)")
        else:
            print("ID3v1 tag        : none")

        print("--- gain info (recognized fields) ---")
        any_field = False
        if info.have_track_gain:
            print(f"  track_gain     : {info.track_gain}")
            any_field = True
        if info.have_track_peak:
            print(f"  track_peak     : {info.track_peak}")
            any_field = True
        if info.have_album_gain:
            print(f"  album_gain     : {info.album_gain}")
            any_field = True
        if info.have_album_peak:
            print(f"  album_peak     : {info.album_peak}")
            any_field = True
        if info.have_min_max_gain:
            print(f"  min/max_gain   : {info.min_gain}, {info.max_gain}")
            any_field = True
        if info.have_album_min_max_gain:
            print(f"  album min/max  : {info.album_min_gain}, {info.album_max_gain}")
            any_field = True
        if info.have_undo:
            print(f"  undo           : L={info.undo_left}, R={info.undo_right}, "
                  f"wrap={info.undo_wrap}")
            any_field = True
        if not any_field:
            print("  (no mp3gain/replaygain fields found)")
        print("")
    return rc


def main(argv):
    if len(argv) < 2:
        _err_usage()

    # Debug sub-commands (Gain dB dev tools) are intercepted before the option
    # parser. Long '--' flags never collide with the 2-char option scheme.
    if argv[1] == "--debug-scan":
        files = argv[2:]
        if not files:
            _err_usage()
        return _run_debug_scan(files)
    if argv[1] == "--debug-tag":
        files = argv[2:]
        if not files:
            _err_usage()
        return _run_debug_tag(files)

    opt = parse_args(argv)

    if opt.database_format:
        _print_database_header(opt)

    if not opt.files:
        _err_usage()

    rc = 0

    # checkTagOnly / deleteTag do not pre-read tags (original read condition).
    if opt.check_tag_only:
        return _run_check_tag_only(opt)

    if opt.delete_tag:
        for path in opt.files:
            rc = _run_delete_tag(opt, path) or rc
        return rc

    # Other paths (undo / direct gain / analysis): pre-read all tags + recalc (D-2).
    tags = _read_all_tags(opt)
    album_recalc = _compute_recalc(opt, tags)

    # Execution branch priority (original main 5.2).
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

    # Analysis path (-r/-a/-e/-x/suggestions/apply/clip) -- C-1/C-2/C-3 + D-2 skip.
    return _run_analysis(opt, tags, album_recalc)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
