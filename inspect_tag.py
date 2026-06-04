"""inspect_tag.py — APEv2 읽기 파서(gaindb/tag.py) 검증용 CLI.

사용:
    python inspect_tag.py <file.mp3> [<file2.mp3> ...]

각 파일에 대해 read_mp3gain_ape_tag 를 호출하고,
파싱된 MP3GainTagInfo / FileTags 를 사람이 읽기 쉽게 출력한다.
"""

import os
import sys

from gaindb.tag import read_mp3gain_ape_tag


def inspect(filename: str) -> None:
    file_size = os.path.getsize(filename)
    info, ft = read_mp3gain_ape_tag(filename)

    print(f"=== {filename} ===")
    print(f"file_size        : {file_size}")
    print(f"tag_offset       : {ft.tag_offset}"
          f"  (audio body ends here; {file_size - ft.tag_offset} tail bytes)")

    # 꼬리 태그 감지 현황
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

    # 인식된 게인 필드
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
    print()


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: python inspect_tag.py <file.mp3> [...]", file=sys.stderr)
        return 1
    for fn in sys.argv[1:]:
        inspect(fn)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
