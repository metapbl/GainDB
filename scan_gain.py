"""
scan_gain.py - MP3 파일의 global_gain 값을 읽어 출력하는 진단 스크립트.

사용법:
    python scan_gain.py "<파일.mp3>"

출력: 프레임 수, 전체 min/max global_gain, 첫 몇 프레임의 게인 값.
원본 mp3gain의 min/max global gain 출력과 비교해 파서 정확도를 검증한다.
"""

import sys

from gaindb.frame import parse_file


def main(argv):
    if len(argv) != 2:
        print('사용법: python scan_gain.py "<파일.mp3>"')
        return 1

    path = argv[1]

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
        print("유효한 MP3 프레임을 찾지 못했습니다.")
        return 1

    ver_name = {3: "MPEG1", 2: "MPEG2", 0: "MPEG2.5"}.get(first_header.mpegver, "?")
    print(f"파일: {path}")
    print(f"형식: {ver_name}, {first_header.samplerate_hz} Hz, "
          f"{first_header.bitrate_kbps} kbps, "
          f"{'mono' if first_header.nchan == 1 else 'stereo'}, "
          f"CRC={'있음' if first_header.has_crc else '없음'}")
    print(f"프레임 수: {frame_count}")
    print(f"min global_gain: {min_gain}")
    print(f"max global_gain: {max_gain}")
    print("첫 프레임들의 global_gain:")
    for off, gains in first_samples:
        print(f"  offset {off}: {gains}")

    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
