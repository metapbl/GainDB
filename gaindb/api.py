"""gaindb/api.py — CLI·GUI·AVD 공유 순수 함수 API 계층.

비파괴·무출력. 분석 결과를 dict 로만 반환한다(파일 수정·stdout 출력 없음).
실제 게인 적용은 apply_gain.apply_track_gain(파괴적, 별개 단계)이 담당한다.

원본 MP3GainGUI 의 DispJunk / Mp3Info.cls 표시 로직을 재현하되 두 가지를
의도적으로 조정한다(근거는 CLAUDE.md 10 진척 로그 참조):
  1) Track Gain 표시 제수는 원본 화면용 근사 1.505 대신 정밀값 5*log10(2) 사용.
     (원본조차 실제 계산 RadioMp3Gain/AlterDb 에는 정밀값을 쓴다.)
  2) 스텝 반올림은 원본 GUI 의 banker's rounding 대신 적용 경로와 동일한
     db_to_steps(round-half-away-from-zero)를 사용한다. 이로써 "표시된 스텝·
     dB·클립 = 실제 apply_track_gain 이 적용할 결과"가 항상 일치한다(표시Only
     정책의 핵심). 0.5 경계의 극소수 곡에서 원본 GUI 표시와 1스텝 다를 수 있다.
"""

from __future__ import annotations

from gaindb.decode import decode_pcm
from gaindb.analysis import (
    analyze_track,
    track_peak,
    db_to_steps,
    DB_PER_STEP,
    NOT_ENOUGH_SAMPLES,
)
from gaindb.writer import scan_gain

# 목표 음량 기준: mp3gain 내부 89 dB ReplayGain 레퍼런스.
# (상대값이며 절대 SPL/LUFS 가 아니다. GUI 라벨/툴팁에 명시할 것.)
DEFAULT_TARGET_DB = 89.0


def analyze_file(path: str, target_db: float = DEFAULT_TARGET_DB) -> dict:
    """한 MP3 를 분석해 GUI 표시용 결과를 반환한다(비파괴, 무출력).

    target_db: 사용자 지정 목표 음량(89 dB 기준 상대). 예: 96.

    반환 dict:
      status        : "ok" | "not_enough_samples"
      track_db      : 89 dB 기준 raw dB (원본 mvarRadiodBGain, mod 미포함).
      volume        : 예측 결과 음량 = target - track_db (원본 DispJunk Volume).
      steps         : 적용 정수 스텝 (db_to_steps, 적용 경로와 동일).
      track_gain_db : steps * DB_PER_STEP (실제 적용될 dB 변화량).
      peak          : 정규화 peak (0~1, 1.0 초과 가능).
      curr_max_amp  : peak * 32768 (원본 CurrMaxAmp, 클립 기준값).
      min_gain,max_gain : scan_gain 결과(프레임 global_gain min/max).
      clip_state    : "none"(검정) | "possible"(파랑 ???) | "definite"(빨강 Y).
    """
    left, right, sample_rate = decode_pcm(path)

    track_db = analyze_track(left, right, sample_rate)
    if track_db is NOT_ENOUGH_SAMPLES:
        return {
            "status": "not_enough_samples", "track_db": None, "volume": None,
            "steps": None, "track_gain_db": None, "peak": None,
            "curr_max_amp": None, "min_gain": None, "max_gain": None,
            "clip_state": "none",
        }

    peak = track_peak(left, right)
    del left, right
    min_gain, max_gain = scan_gain(path)

    curr_max_amp = peak * 32768.0
    modify_db = target_db - DEFAULT_TARGET_DB

    volume = DEFAULT_TARGET_DB + modify_db - track_db

    steps = db_to_steps(track_db + modify_db)
    track_gain_db = steps * DB_PER_STEP

    if curr_max_amp * (2.0 ** (steps / 4.0)) > 32767.0:
        if curr_max_amp * (2.0 ** ((83.0 - volume) / 6.0206)) > 32767.0:
            clip_state = "possible"
        else:
            clip_state = "definite"
    else:
        clip_state = "none"

    return {
        "status": "ok",
        "track_db": track_db,
        "volume": round(volume, 1),
        "steps": steps,
        "track_gain_db": round(track_gain_db, 1),
        "peak": peak,
        "curr_max_amp": round(curr_max_amp),
        "min_gain": min_gain,
        "max_gain": max_gain,
        "clip_state": clip_state,
    }
