"""
apply_gain.py - MP3 파일의 global_gain 을 무손실 조정하는 스크립트.

사용법:
    python apply_gain.py <게인스텝> "<파일.mp3>"

게인스텝은 정수. 1스텝 = 약 1.5dB. 양수=키우기, 음수=줄이기.
주의: 파일을 직접 수정한다. 되돌리려면 반대 부호로 다시 실행.
"""

import sys

from gaindb.writer import apply_gain


def main(argv):
    if len(argv) != 3:
        print('사용법: python apply_gain.py <게인스텝> "<파일.mp3>"')
        return 1

    try:
        change = int(argv[1])
    except ValueError:
        print("게인스텝은 정수여야 합니다.")
        return 1

    path = argv[2]

    count = apply_gain(path, change)
    print(f"{path}")
    print(f"게인 {change:+d} 스텝 (약 {change * 1.5:+.1f} dB) 적용 완료: {count}개 프레임 수정")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
