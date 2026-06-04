"""
gaindb/analysis.py

ReplayGain 분석기 (Track gain).

clean-room 구현: 필터 계수는 원본 C 소스가 아니라 ReplayGain 공식 사양
(Hydrogenaudio "Original ReplayGain specification", Tables 1·2)에서 옮겼다.
사양에 수치가 명시된 44.1 kHz·48 kHz 두 샘플레이트만 지원한다.
나머지 샘플레이트는 사양에 계수가 없으므로 미지원(ValueError)으로 둔다.

알고리즘 사양:
  1) 입력 PCM 을 10차 yulewalk IIR → 2차 Butterworth(150Hz HPF) 캐스케이드로 필터.
  2) 필터링된 신호를 50ms 윈도우로 잘라 평균제곱(양 채널 평균)을 dB 로 환산.
  3) dB 값을 0.01dB 해상도 히스토그램(0..120dB)에 누적.
  4) 누적분포 상위 95퍼센타일 지점의 음량을 구해 PINK_REF 에서 빼 게인 산출.

dB 산출식은 원본과 동일한 등가식(10*log10(meanSquare))을 따른다 —
표준 mp3gain 결과와 일치시켜 1단계 apply_gain 과 정합하기 위함.
"""

from __future__ import annotations

import math

import numpy as np
from scipy.signal import lfilter

# --- 사양 상수 (ReplayGain 공식 사양) ---
RMS_PERCENTILE = 0.95        # 상위 95퍼센타일
STEPS_PER_DB = 100           # 히스토그램 0.01dB 해상도
MAX_DB = 120                 # 히스토그램 범위 0..120 dB
RMS_WINDOW_MS = 50           # RMS 윈도우 길이(ms)
PINK_REF = 64.82             # 캘리브레이션 기준값(dB)

# dB → MP3 게인 스텝 변환 제수. 원본 mp3gain 과 동일하게 5*log10(2) 를 쓴다.
# 디코더가 global_gain 을 2^(gain/4) 로 적용 → 1스텝 = 20*log10(2^0.25) = 5*log10(2) dB.
_DB_PER_STEP_DIVISOR = 5.0 * math.log10(2.0)

# --- 공식 사양 계수 (Tables 1·2). lfilter(b, a, x) 규약: a[0]=1.0 ---
# Yulewalk: b = [b0..b10], a = [1.0, a1..a10]
# Butterworth: b = [b0, b1, b2], a = [1.0, a1, a2]

_YULE_44100_B = [
    0.05418656406430, -0.02911007808948, -0.00848709379851, -0.00851165645469,
    -0.00834990904936,  0.02245293253339, -0.02596338512915,  0.01624864962975,
    -0.00240879051584,  0.00674613682247, -0.00187763777362,
]
_YULE_44100_A = [
    1.0, -3.47845948550071, 6.36317777566148, -8.54751527471874,
    9.47693607801280, -8.81498681370155, 6.85401540936998, -4.39470996079559,
    2.19611684890774, -0.75104302451432, 0.13149317958808,
]
_BUTTER_44100_B = [0.98500175787242, -1.97000351574484, 0.98500175787242]
_BUTTER_44100_A = [1.0, -1.96977855582618, 0.97022847566350]

_YULE_48000_B = [
    0.03857599435200, -0.02160367184185, -0.00123395316851, -0.00009291677959,
    -0.01655260341619,  0.02161526843274, -0.02074045215285,  0.00594298065125,
     0.00306428023191,  0.00012025322027,  0.00288463683916,
]
_YULE_48000_A = [
    1.0, -3.84664617118067, 7.81501653005538, -11.34170355132042,
    13.05504219327545, -12.28759895145294, 9.48293806319790, -5.87257861775999,
    2.75465861874613, -0.86984376593551, 0.13919314567432,
]
_BUTTER_48000_B = [0.98621192462708, -1.97242384925416, 0.98621192462708]
_BUTTER_48000_A = [1.0, -1.97223372919527, 0.97261396931306]

# 샘플레이트 → (yule_b, yule_a, butter_b, butter_a)
_FILTER_COEFFS = {
    44100: (_YULE_44100_B, _YULE_44100_A, _BUTTER_44100_B, _BUTTER_44100_A),
    48000: (_YULE_48000_B, _YULE_48000_A, _BUTTER_48000_B, _BUTTER_48000_A),
}

# 게인 산출에 충분한 샘플이 없을 때.
NOT_ENOUGH_SAMPLES = object()


def _filter_channel(samples: np.ndarray, yb, ya, bb, ba) -> np.ndarray:
    """한 채널에 yulewalk → Butterworth 캐스케이드를 적용한다."""
    stepped = lfilter(yb, ya, samples)
    out = lfilter(bb, ba, stepped)
    return out


def _loudness_histogram(
    left: np.ndarray, right: np.ndarray, sample_rate: int
) -> np.ndarray:
    """
    필터 + 50ms RMS + dB 환산 후 0.01dB 히스토그램(길이 STEPS_PER_DB*MAX_DB)을 반환.
    """
    if sample_rate not in _FILTER_COEFFS:
        raise ValueError(
            f"지원하지 않는 샘플레이트입니다: {sample_rate} Hz "
            f"(현재 지원: {sorted(_FILTER_COEFFS)})"
        )

    yb, ya, bb, ba = _FILTER_COEFFS[sample_rate]
    lout = _filter_channel(left, yb, ya, bb, ba)
    rout = _filter_channel(right, yb, ya, bb, ba)

    window = int(np.ceil(sample_rate * RMS_WINDOW_MS / 1000.0))
    nbins = STEPS_PER_DB * MAX_DB
    hist = np.zeros(nbins, dtype=np.int64)

    n_windows = lout.size // window
    if n_windows == 0:
        return hist  # 윈도우 하나도 못 채움 → 빈 히스토그램

    trim = n_windows * window
    lsq = lout[:trim] ** 2
    rsq = rout[:trim] ** 2

    # 윈도우별 합산: (n_windows, window) 로 reshape 후 행 합.
    lsum = lsq.reshape(n_windows, window).sum(axis=1)
    rsum = rsq.reshape(n_windows, window).sum(axis=1)

    # 양 채널 평균제곱. 원본과 동일한 등가식: 10*log10(meanSquare).
    mean_sq = (lsum + rsum) / window * 0.5 + 1.0e-37
    db = STEPS_PER_DB * 10.0 * np.log10(mean_sq)

    ival = db.astype(np.int64)
    np.clip(ival, 0, nbins - 1, out=ival)

    # 각 칸의 빈도 누적.
    np.add.at(hist, ival, 1)
    return hist


def _gain_from_histogram(hist: np.ndarray):
    """
    히스토그램에서 상위 95퍼센타일 지점을 찾아 게인(dB)을 산출.
    충분한 샘플이 없으면 NOT_ENOUGH_SAMPLES 를 반환.
    """
    total = int(hist.sum())
    if total == 0:
        return NOT_ENOUGH_SAMPLES

    upper = int(np.ceil(total * (1.0 - RMS_PERCENTILE)))
    # 위(큰 dB)에서부터 빈도를 빼 나가며 95퍼센타일 경계 칸을 찾는다.
    i = hist.size
    while i > 0:
        i -= 1
        upper -= int(hist[i])
        if upper <= 0:
            break

    return float(PINK_REF - i / float(STEPS_PER_DB))


def analyze_track(
    left: np.ndarray, right: np.ndarray, sample_rate: int
) -> float:
    """
    Track replay gain(dB)을 산출해 반환한다.

    left, right: decode 가 준 ±32768 스케일 float64 채널.
    sample_rate: 44100 또는 48000 (그 외는 ValueError).
    충분한 샘플이 없으면 NOT_ENOUGH_SAMPLES 를 반환.
    """
    hist = _loudness_histogram(left, right, sample_rate)
    return _gain_from_histogram(hist)

def track_histogram(
    left: np.ndarray, right: np.ndarray, sample_rate: int
) -> np.ndarray:
    """
    한 곡의 라우드니스 히스토그램(0.01dB 해상도, 길이 STEPS_PER_DB*MAX_DB)을 반환한다.

    Album gain 누적용. 여러 곡의 반환값을 단순 합산하면 앨범 전체를 하나의 긴
    신호로 취급한 것과 수학적으로 동일하다(곡 길이가 자동으로 가중치가 됨).
    샘플레이트 검증·필터·RMS 는 _loudness_histogram 이 그대로 수행한다.
    """
    return _loudness_histogram(left, right, sample_rate)


def gain_from_histograms(hists):
    """
    여러 곡의 히스토그램을 누적 합산한 뒤 Album replay gain(dB)을 산출한다.

    hists: track_histogram 이 반환한 np.ndarray 들의 시퀀스.
    충분한 샘플이 없으면(빈 시퀀스 또는 전체 빈도 0) NOT_ENOUGH_SAMPLES 를 반환.
    개별 곡의 부족 여부는 따지지 않고 누적 후 한 번만 판정한다.
    """
    total = None
    for h in hists:
        total = h.copy() if total is None else total + h
    if total is None:
        return NOT_ENOUGH_SAMPLES
    return _gain_from_histogram(total)


def db_to_steps(db_change: float) -> int:
    """
    ReplayGain dB 변화량을 정수 MP3 게인 스텝으로 양자화한다.

    원본 mp3gain 과 동일한 round-half-away-from-zero 방식:
    0 방향으로 자른 뒤 분수부가 0.5 이상이면 절댓값을 1 키운다.
    파이썬 round() 의 banker's rounding 과 0.5 경계에서 어긋나므로 쓰지 않는다.
    """
    raw = db_change / _DB_PER_STEP_DIVISOR
    truncated = int(raw)  # int() 는 0 방향 절단
    frac = abs(raw) - abs(truncated)
    if frac < 0.5:
        return truncated
    return truncated + (-1 if raw < 0 else 1)
