"""
apply_gain.py - MP3 파일의 global_gain 을 무손실 조정하는 스크립트.

사용법:
    수동:  python apply_gain.py <게인스텝> "<파일.mp3>"
    자동:  python apply_gain.py auto "<파일.mp3>"

수동 모드: 게인스텝은 정수. 1스텝 = 약 1.5dB. 양수=키우기, 음수=줄이기.
자동 모드: ReplayGain 분석으로 89dB 기준 적정 스텝을 계산해 적용한다.
주의: 파일을 직접 수정한다. 되돌리려면 반대 부호로 다시 실행(수동) 하거나 undo(추후 단계).
"""

import sys

from gaindb.decode import decode_pcm
from gaindb.analysis import analyze_track, db_to_steps, NOT_ENOUGH_SAMPLES
from gaindb.writer import apply_gain


def apply_track_gain(
    path: str,
    db_gain_mod: float = 0.0,
    mp3_gain_mod: int = 0,
    wrap: bool = False,
) -> dict:
    """
    한 MP3 파일에 Track ReplayGain 을 무손실 적용한다.

    흐름: PCM 디코딩 → ReplayGain 분석(dB) → 정수 스텝 양자화 → global_gain 적용.

    db_gain_mod:  변환 전 더하는 보정 dB(원본 -d). 89dB 기준 유지를 위해 변환 직전에 더한다.
    mp3_gain_mod: 변환 후 더하는 정수 스텝 보정(원본 -m).
    wrap:         True 면 0~255 클램프 대신 wrap(원본 -w). 기본 False.

    반환: 결과 요약 dict.
      - status: "ok" | "no_change" | "not_enough_samples"
      - db_gain: 분석 dB(89dB 기준). not_enough_samples 면 None.
      - steps: 적용한 정수 스텝. not_enough_samples 면 None.
      - frames_changed: 실제 수정한 프레임 수.
    """
    left, right, sample_rate = decode_pcm(path)

    db_gain = analyze_track(left, right, sample_rate)
    if db_gain is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples",
            "db_gain": None,
            "steps": None,
            "frames_changed": 0,
        }

    steps = db_to_steps(db_gain + db_gain_mod) + mp3_gain_mod

    if steps == 0:
        # 이미 목표 음량 수준 → 파일을 건드리지 않는다(원본 동작).
        return {
            "status": "no_change",
            "db_gain": db_gain,
            "steps": 0,
            "frames_changed": 0,
        }

    changed = apply_gain(path, steps, wrap=wrap)
    return {
        "status": "ok",
        "db_gain": db_gain,
        "steps": steps,
        "frames_changed": changed,
    }


def _run_manual(change: int, path: str) -> int:
    count = apply_gain(path, change)
    print(f"{path}")
    print(f"게인 {change:+d} 스텝 (약 {change * 1.5:+.1f} dB) 적용 완료: {count}개 프레임 수정")
    return 0


def _run_auto(path: str) -> int:
    result = apply_track_gain(path)
    print(f"{path}")
    if result["status"] == "not_enough_samples":
        print("분석할 샘플이 부족합니다. 적용하지 않았습니다.")
        return 1
    if result["status"] == "no_change":
        print(
            f"분석 게인 {result['db_gain']:+.2f} dB → 0 스텝. "
            "이미 목표 음량 수준이라 변경하지 않았습니다."
        )
        return 0
    steps = result["steps"]
    print(
        f"분석 게인 {result['db_gain']:+.2f} dB → {steps:+d} 스텝 "
        f"(약 {steps * 1.5:+.1f} dB) 적용 완료: {result['frames_changed']}개 프레임 수정"
    )
    return 0


def main(argv):
    if len(argv) != 3:
        print('사용법(수동): python apply_gain.py <게인스텝> "<파일.mp3>"')
        print('사용법(자동): python apply_gain.py auto "<파일.mp3>"')
        return 1

    mode_arg = argv[1]
    path = argv[2]

    if mode_arg.lower() == "auto":
        return _run_auto(path)

    try:
        change = int(mode_arg)
    except ValueError:
        print("첫 인자는 정수 게인스텝이거나 'auto' 여야 합니다.")
        return 1

    return _run_manual(change, path)


if __name__ == "__main__":
    sys.exit(main(sys.argv))
