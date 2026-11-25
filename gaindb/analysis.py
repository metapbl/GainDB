# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
# SPDX-FileCopyrightText: 2001-2009 David Robinson and Glen Sawyer
#
# The algorithm and the filter coefficient tables in this module follow
# the ReplayGain proposal by David Robinson (replaygain.org) and the
# reference implementation ReplayGainAnalysis / gain_analysis.c
# (Copyright (C) 2001-2009 David Robinson and Glen Sawyer; improvements
# by Frank Klemm and Marcel Mueller), licensed under the GNU LGPL v2.1
# or later. The Python code here is a new vectorized implementation
# (numpy) and is distributed under the same LGPL terms.
"""
gaindb/analysis.py

ReplayGain 분석기 (Track gain / Album gain).

알고리즘·필터 계수의 출처: ReplayGain 공개 제안(replaygain.org, David
Robinson)과 그 레퍼런스 구현 ReplayGainAnalysis(gain_analysis.c,
LGPL-2.1-or-later)를 따른다. 이 프로젝트가 쓰는 전 샘플레이트
(44.1k·48k·32k / 24k·22.05k·16k / 12k·11.025k·8k)의 yulewalk·Butterworth
계수는 ReplayGain 공개 사양이 수치로 정의하는 표준값이며, 여러 구현이
사양처럼 공유하는 값이다. 그 수치를 scipy lfilter 규약(b/a 분리,
a[0]=1.0)에 맞게 재배치해 전사했다(사양의 표는 한 배열에 b·a 계수를 교차
저장하는 형태이므로, 같은 수치를 lfilter 형식으로 옮겼을 뿐 값은 동일하다).
코드 자체는 C 레퍼런스와 달리 numpy 벡터화로 새로 작성했으며,
프로젝트 전체와 함께 LGPL-2.1-or-later 로 배포된다. 상세 경위는 CLAUDE.md
10 진척 로그(6단계) 참조. 사실 고지는 NOTICE/README 에서 다룬다.

알고리즘 사양:
  1) 입력 PCM 을 10차 yulewalk IIR → 2차 Butterworth(150Hz HPF) 캐스케이드로 필터.
  2) 필터링된 신호를 50ms 윈도우로 잘라 평균제곱(양 채널 평균)을 dB 로 환산.
  3) dB 값을 0.01dB 해상도 히스토그램(0..120dB)에 누적.
  4) 누적분포 상위 95퍼센타일 지점의 음량을 구해 PINK_REF 에서 빼 게인 산출.

dB 산출식은 ReplayGain 사양의 등가식(10*log10(meanSquare))을 따른다 — mp3gain
과 결과 수치를 일치시켜 apply_gain 과 정합하기 위함이다.
"""

from __future__ import annotations

import math

import numpy as np

# --- 사양 상수 (ReplayGain 공식 사양) ---
RMS_PERCENTILE = 0.95        # 상위 95퍼센타일
STEPS_PER_DB = 100           # 히스토그램 0.01dB 해상도
MAX_DB = 120                 # 히스토그램 범위 0..120 dB
RMS_WINDOW_MS = 50           # RMS 윈도우 길이(ms)
PINK_REF = 64.82             # 캘리브레이션 기준값(dB)

# dB → MP3 게인 스텝 변환 제수. mp3gain 과 동일한 결과가 되도록 5*log10(2) 를 쓴다.
# 디코더가 global_gain 을 2^(gain/4) 로 적용 → 1스텝 = 20*log10(2^0.25) = 5*log10(2) dB.
_DB_PER_STEP_DIVISOR = 5.0 * math.log10(2.0)

# 공개 별칭: 1 스텝당 dB(정밀값). api/GUI/AVD 가 import 해 쓰는 표시·계산 상수.
DB_PER_STEP = _DB_PER_STEP_DIVISOR

# --- 필터 계수 ---
# lfilter(b, a, x) 규약: a[0]=1.0. Yulewalk: b=[b0..b10], a=[1.0, a1..a10].
# Butterworth: b=[b0, b1, b2], a=[1.0, a1, a2].
#
# 전 샘플레이트 계수는 ReplayGain 공개 사양이 정의하는 표준값이다(레퍼런스
# 구현 gain_analysis.c 의 테이블과 동일한 수치). 그 수치를 lfilter 규약에
# 맞게 재배치해 전사했다. 상세는 위 모듈 docstring 및 CLAUDE.md 10 진척
# 로그(6단계) 참조.

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

_YULE_32000_B = [
    0.15457299681924, -0.09331049056315, -0.06247880153653,  0.02163541888798,
    -0.05588393329856,  0.04781476674921,  0.00222312597743,  0.03174092540049,
    -0.01390589421898,  0.00651420667831, -0.00881362733839,
]
_YULE_32000_A = [
    1.0, -2.37898834973084, 2.84868151156327, -2.64577170229825,
    2.23697657451713, -1.67148153367602, 1.00595954808547, -0.45953458054983,
    0.16378164858596, -0.05032077717131, 0.02347897407020,
]
_BUTTER_32000_B = [0.97938932735214, -1.95877865470428, 0.97938932735214]
_BUTTER_32000_A = [1.0, -1.95835380975398, 0.95920349965459]

_YULE_24000_B = [
    0.30296907319327, -0.22613988682123, -0.08587323730772,  0.03282930172664,
    -0.00915702933434, -0.02364141202522, -0.00584456039913,  0.06276101321749,
    -0.00000828086748,  0.00205861885564, -0.02950134983287,
]
_YULE_24000_A = [
    1.0, -1.61273165137247, 1.07977492259970, -0.25656257754070,
    -0.16276719120440, -0.22638893773906, 0.39120800788284, -0.22138138954925,
    0.04500235387352, 0.02005851806501, 0.00302439095741,
]
_BUTTER_24000_B = [0.97531843204928, -1.95063686409857, 0.97531843204928]
_BUTTER_24000_A = [1.0, -1.95002759149878, 0.95124613669835]

_YULE_22050_B = [
    0.33642304856132, -0.25572241425570, -0.11828570177555,  0.11921148675203,
    -0.07834489609479, -0.00469977914380, -0.00589500224440,  0.05724228140351,
     0.00832043980773, -0.01635381384540, -0.01760176568150,
]
_YULE_22050_A = [
    1.0, -1.49858979367799, 0.87350271418188, 0.12205022308084,
    -0.80774944671438, 0.47854794562326, -0.12453458140019, -0.04067510197014,
    0.08333755284107, -0.04237348025746, 0.02977207319925,
]
_BUTTER_22050_B = [0.97316523498161, -1.94633046996323, 0.97316523498161]
_BUTTER_22050_A = [1.0, -1.94561023566527, 0.94705070426118]

_YULE_16000_B = [
    0.44915256608450, -0.14351757464547, -0.22784394429749, -0.01419140100551,
     0.04078262797139, -0.12398163381748,  0.04097565135648,  0.10478503600251,
    -0.01863887810927, -0.03193428438915,  0.00541907748707,
]
_YULE_16000_A = [
    1.0, -0.62820619233671, 0.29661783706366, -0.37256372942400,
    0.00213767857124, -0.42029820170918, 0.22199650564824, 0.00613424350682,
    0.06747620744683, 0.05784820375801, 0.03222754072173,
]
_BUTTER_16000_B = [0.96454515552826, -1.92909031105652, 0.96454515552826]
_BUTTER_16000_A = [1.0, -1.92783286977036, 0.93034775234268]

_YULE_12000_B = [
    0.56619470757641, -0.75464456939302,  0.16242137742230,  0.16744243493672,
    -0.18901604199609,  0.30931782841830, -0.27562961986224,  0.00647310677246,
     0.08647503780351, -0.03788984554840, -0.00588215443421,
]
_YULE_12000_A = [
    1.0, -1.04800335126349, 0.29156311971249, -0.26806001042947,
    0.00819999645858, 0.45054734505008, -0.33032403314006, 0.06739368333110,
    -0.04784254229033, 0.01639907836189, 0.01807364323573,
]
_BUTTER_12000_B = [0.96009142950541, -1.92018285901082, 0.96009142950541]
_BUTTER_12000_A = [1.0, -1.91858953033784, 0.92177618768381]

_YULE_11025_B = [
    0.58100494960553, -0.53174909058578, -0.14289799034253,  0.17520704835522,
     0.02377945217615,  0.15558449135573, -0.25344790059353,  0.01628462406333,
     0.06920467763959, -0.03721611395801, -0.00749618797172,
]
_YULE_11025_A = [
    1.0, -0.51035327095184, -0.31863563325245, -0.20256413484477,
    0.14728154134330, 0.38952639978999, -0.23313271880868, -0.05246019024463,
    -0.02505961724053, 0.02442357316099, 0.01818801111503,
]
_BUTTER_11025_B = [0.95856916599601, -1.91713833199203, 0.95856916599601]
_BUTTER_11025_A = [1.0, -1.91542108074780, 0.91885558323625]

_YULE_8000_B = [
    0.53648789255105, -0.42163034350696, -0.00275953611929,  0.04267842219415,
    -0.10214864179676,  0.14590772289388, -0.02459864859345, -0.11202315195388,
    -0.04060034127000,  0.04788665548180, -0.02217936801134,
]
_YULE_8000_A = [
    1.0, -0.25049871956020, -0.43193942311114, -0.03424681017675,
    -0.04678328784242, 0.26408300200955, 0.15113130533216, -0.17556493366449,
    -0.18823009262115, 0.05477720428674, 0.04704409688120,
]
_BUTTER_8000_B = [0.94597685600279, -1.89195371200558, 0.94597685600279]
_BUTTER_8000_A = [1.0, -1.88903307939452, 0.89487434461664]

# 샘플레이트 → (yule_b, yule_a, butter_b, butter_a)
_FILTER_COEFFS = {
    44100: (_YULE_44100_B, _YULE_44100_A, _BUTTER_44100_B, _BUTTER_44100_A),
    48000: (_YULE_48000_B, _YULE_48000_A, _BUTTER_48000_B, _BUTTER_48000_A),
    32000: (_YULE_32000_B, _YULE_32000_A, _BUTTER_32000_B, _BUTTER_32000_A),
    24000: (_YULE_24000_B, _YULE_24000_A, _BUTTER_24000_B, _BUTTER_24000_A),
    22050: (_YULE_22050_B, _YULE_22050_A, _BUTTER_22050_B, _BUTTER_22050_A),
    16000: (_YULE_16000_B, _YULE_16000_A, _BUTTER_16000_B, _BUTTER_16000_A),
    12000: (_YULE_12000_B, _YULE_12000_A, _BUTTER_12000_B, _BUTTER_12000_A),
    11025: (_YULE_11025_B, _YULE_11025_A, _BUTTER_11025_B, _BUTTER_11025_A),
    8000:  (_YULE_8000_B,  _YULE_8000_A,  _BUTTER_8000_B,  _BUTTER_8000_A),
}

# 게인 산출에 충분한 샘플이 없을 때.
NOT_ENOUGH_SAMPLES = object()


# --- numpy 블록 IIR (scipy lfilter 대체, D118) ---
# yulewalk → Butterworth 캐스케이드를 상태공간 하나(상태 = [yule 상태, butter
# 상태], 각각 lfilter 의 zi 와 같은 전치 직접형 II 형식)로 합친다. 블록(_IIR_BLOCK
# 샘플) 안의 출력은 행렬곱으로, 블록 시작 상태는 그룹(_IIR_GROUP 블록) 단위
# 행렬곱으로 구하고 그룹 사이만 순차로 넘긴다. 좌우 채널은 함께 처리한다.
_IIR_BLOCK = 128
_IIR_GROUP = 32
_IIR_MATS: dict = {}


def _state_space(b, a):
    """lfilter(b, a) 와 같은 (A, B, C, D): z' = A z + B x, y = C z + D x."""
    n = max(len(a), len(b)) - 1
    bn = np.concatenate((np.asarray(b, float), np.zeros(n + 1 - len(b)))) / a[0]
    an = np.concatenate((np.asarray(a, float), np.zeros(n + 1 - len(a)))) / a[0]
    A = np.zeros((n, n))
    A[:, 0] = -an[1:]
    A[:-1, 1:] = np.eye(n - 1)
    B = bn[1:] - an[1:] * bn[0]
    C = np.zeros(n)
    C[0] = 1.0
    return A, B, C, bn[0]


def _iir_mats(sample_rate: int):
    """샘플레이트별 캐스케이드 블록 행렬 (T, O, R, A, P, M) 을 만들어 캐시한다."""
    mats = _IIR_MATS.get(sample_rate)
    if mats is not None:
        return mats
    yb, ya, bb, ba = _FILTER_COEFFS[sample_rate]
    A1, B1, C1, D1 = _state_space(yb, ya)
    A2, B2, C2, D2 = _state_space(bb, ba)
    n1, n2 = A1.shape[0], A2.shape[0]
    A = np.zeros((n1 + n2, n1 + n2))
    A[:n1, :n1] = A1
    A[n1:, :n1] = np.outer(B2, C1)
    A[n1:, n1:] = A2
    B = np.concatenate((B1, B2 * D1))
    C = np.concatenate((D2 * C1, C2))
    D = D2 * D1

    L, G = _IIR_BLOCK, _IIR_GROUP
    n = n1 + n2
    O = np.empty((L, n))                   # O[k] = C A^k: 초기 상태 → y[k]
    Ak = np.eye(n)
    for k in range(L):
        O[k] = C @ Ak
        Ak = A @ Ak
    AL = Ak                                # A^L: 블록 하나만큼 상태 진행
    h = np.empty(L)                        # 임펄스 응답
    h[0] = D
    h[1:] = O[:-1] @ B
    T = np.zeros((L, L))                   # 영상태 응답(하삼각 토플리츠)
    for k in range(L):
        T[k:, k] = h[: L - k]
    R = np.empty((n, L))                   # R[:, k] = A^(L-1-k) B: x[k] → 블록 끝 상태
    v = B.copy()
    for k in range(L - 1, -1, -1):
        R[:, k] = v
        v = A @ v
    # 상태는 행벡터로 다룬다(s' = s @ A^T). P[k] = (A^L)^T 의 k 제곱.
    P = np.empty((G + 1, n, n))
    P[0] = np.eye(n)
    for k in range(G):
        P[k + 1] = P[k] @ AL.T
    # M: 그룹 안 블록별 입력 기여(XR) → 그룹 안 k 번째 블록 시작 상태(k = 0..G).
    M = np.zeros((G * n, (G + 1) * n))
    for j in range(G):
        for k in range(j + 1, G + 1):
            M[j * n:(j + 1) * n, k * n:(k + 1) * n] = P[k - 1 - j]
    mats = (T, O, R, A, P, M)
    _IIR_MATS[sample_rate] = mats
    return mats


def _iir(sample_rate: int, x: np.ndarray, zi: np.ndarray):
    """캐스케이드 필터. x: (채널, N), zi: (채널, 상태 수) → (y, zf).

    lfilter(bb, ba, lfilter(yb, ya, x, zi=zi[:, :10]), zi=zi[:, 10:]) 와 같은 값.
    같은 입력이라도 블록·그룹 경계가 달라지면 반올림이 달라질 수 있으므로,
    스트리밍(TrackAnalyzer)은 곡 시작 기준 그룹 경계에 맞춰서만 부른다.
    """
    T, O, R, A, P, M = _iir_mats(sample_rate)
    L, G = _IIR_BLOCK, _IIR_GROUP
    ch, N = x.shape
    n = A.shape[0]
    nb, r = divmod(N, L)
    s = np.array(zi, dtype=np.float64)
    if not nb:
        y = np.empty((ch, N))
    else:
        X = x[:, : nb * L].reshape(ch * nb, L)
        ng = -(-nb // G)
        XR = np.zeros((ch, ng * G, n))     # 마지막 그룹의 빈 블록은 0 입력
        XR[:, :nb] = (X @ R.T).reshape(ch, nb, n)
        Q = (XR.reshape(ch * ng, G * n) @ M).reshape(ch, ng, G + 1, n)
        SG = np.empty((ch, ng, n))         # 그룹 시작 상태
        PG = P[G]
        for g in range(ng):
            SG[:, g] = s
            s = s @ PG + Q[:, g, G]
        S = (SG @ P[:G].transpose(1, 0, 2).reshape(n, G * n)).reshape(ch, ng, G, n)
        S += Q[:, :, :G]
        S = S.reshape(ch, ng * G, n)
        if nb < ng * G:
            s = S[:, nb].copy()            # 마지막 실제 블록 끝 상태
        Y = X @ T.T
        Y += S[:, :nb].reshape(ch * nb, n) @ O.T
        if not r:
            return Y.reshape(ch, N), s
        y = np.empty((ch, N))
        y[:, : nb * L] = Y.reshape(ch, nb * L)
    xt = x[:, nb * L:]
    y[:, nb * L:] = xt @ T[:r, :r].T + s @ O[:r].T
    s = s @ np.linalg.matrix_power(A, r).T + xt @ R[:, L - r:].T
    return y, s


def _loudness_histogram(
    left: np.ndarray, right: np.ndarray, sample_rate: int
) -> np.ndarray:
    """
    필터 + 50ms RMS + dB 환산 후 0.01dB 히스토그램(길이 STEPS_PER_DB*MAX_DB)을 반환.

    스트리밍과 결과가 완전히 같도록 TrackAnalyzer 에 한 번에 먹인다 (D010).
    """
    an = TrackAnalyzer(sample_rate)
    an.feed(left, right)
    return an.histogram()


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
    sample_rate: ReplayGain 사양의 지원 샘플레이트
        (44100·48000·32000·24000·22050·16000·12000·11025·8000).
        그 외는 ValueError.
    충분한 샘플이 없으면 NOT_ENOUGH_SAMPLES 를 반환.
    """
    hist = _loudness_histogram(left, right, sample_rate)
    return _gain_from_histogram(hist)


class TrackAnalyzer:
    """스트리밍(청크 누적) 라우드니스 분석기.

    곡 전체를 메모리에 올리지 않고 청크를 순차로 먹여 히스토그램·peak 을
    누적한다. 초장시간 곡(수 시간)도 청크 하나 크기의 메모리로 처리하기 위한
    것이며, 결과는 일괄 처리(_loudness_histogram)와 수학적으로 동일하다.

    동일성의 근거:
      - 필터: 입력을 곡 시작 기준 그룹(_IIR_BLOCK*_IIR_GROUP) 경계에 맞춰
        버퍼링하고, 상태를 이어받아 완전한 그룹만 통과시킨다. 곡 끝 자투리는 histogram()/result()
        에서 한 번 처리한다. 청크를 어떻게 나눠도 같은 블록 연산이 되므로 일괄
        경로(_loudness_histogram 도 이 클래스를 씀)와 부동소수까지 같다.
      - RMS 윈도우: 필터 '출력'을 윈도우(50ms)로 자르는 것은 일괄 경로와 같다.
        청크 경계가 윈도우 경계와 어긋날 수 있으므로, 완전한 윈도우만 이번에
        처리하고 남는 자투리(필터 출력)는 버퍼에 남겨 다음 feed 에 이어붙인다.
        곡 끝의 마지막 불완전 윈도우는 일괄 경로처럼 버려진다(result 에서 처리
        안 함).
      - peak: 필터 전 원샘플의 좌우 abs 최댓값을 청크마다 갱신(전체 최댓값 =
        청크별 최댓값의 최댓값). track_peak 과 동일 정의(/32768).

    사용:
      an = TrackAnalyzer(sample_rate)
      an.feed(left_chunk, right_chunk)   # 여러 번
      db = an.result()                   # 최종 게인(dB) 또는 NOT_ENOUGH_SAMPLES
      peak = an.peak_normalized()        # 정규화 peak(0~1)
      hist = an.histogram()              # Album 누적용 히스토그램
    """

    def __init__(self, sample_rate: int) -> None:
        if sample_rate not in _FILTER_COEFFS:
            raise ValueError(
                f"Unsupported sample rate: {sample_rate} Hz "
                f"(currently supported: {sorted(_FILTER_COEFFS)})"
            )
        self._sample_rate = sample_rate

        self._window = int(np.ceil(sample_rate * RMS_WINDOW_MS / 1000.0))
        self._nbins = STEPS_PER_DB * MAX_DB
        self._hist = np.zeros(self._nbins, dtype=np.int64)

        # 필터 상태(좌/우 × [yule, butter]). 0 으로 시작 = lfilter 의 zi 없는 호출과 같음.
        self._zi = np.zeros((2, _iir_mats(sample_rate)[3].shape[0]))

        # 필터 출력의 윈도우 자투리 버퍼(다음 feed 에 이어붙일 제곱합용 원신호).
        self._buf_l = np.empty(0, dtype=np.float64)
        self._buf_r = np.empty(0, dtype=np.float64)

        # 필터 입력의 그룹 자투리 버퍼(좌/우). 그룹 경계를 곡 시작 기준으로 고정한다.
        self._in = np.empty((2, 0), dtype=np.float64)
        self._flushed = False

        self._peak_raw = 0.0  # 필터 전 원샘플 abs 최댓값(±32768 스케일)

    def feed(self, left: np.ndarray, right: np.ndarray) -> None:
        """오디오 청크(±32768 스케일 float)를 누적한다. 좌우 길이는 같아야 한다."""
        if left.size == 0:
            return

        # peak: 필터 전 원샘플 기준(track_peak 정의와 동일).
        lmax = float(np.abs(left).max())
        rmax = float(np.abs(right).max())
        if lmax > self._peak_raw:
            self._peak_raw = lmax
        if rmax > self._peak_raw:
            self._peak_raw = rmax

        # 입력 자투리 + 이번 청크를 한 버퍼에 모으고, 완전한 그룹만 필터에 넣는다.
        rest = self._in.shape[1]
        x = np.empty((2, rest + left.size))
        x[:, :rest] = self._in
        x[0, rest:] = left
        x[1, rest:] = right
        full = x.shape[1] - x.shape[1] % (_IIR_BLOCK * _IIR_GROUP)
        self._in = x[:, full:]
        if full:
            self._filter_and_accumulate(x[:, :full])

    def _flush(self) -> None:
        """곡 끝의 블록 자투리 입력을 필터에 넣는다(한 번만)."""
        if self._flushed:
            return
        self._flushed = True
        if self._in.shape[1]:
            self._filter_and_accumulate(self._in)

    def _filter_and_accumulate(self, x: np.ndarray) -> None:
        # 필터: 상태를 이어받아 연속 통과.
        (lo, ro), self._zi = _iir(self._sample_rate, x, self._zi)

        # 직전 자투리 + 이번 필터 출력을 이어붙인다.
        lout = np.concatenate((self._buf_l, lo)) if self._buf_l.size else lo
        rout = np.concatenate((self._buf_r, ro)) if self._buf_r.size else ro

        window = self._window
        n_windows = lout.size // window
        if n_windows == 0:
            # 완전한 윈도우 없음: 전부 자투리로 보관.
            self._buf_l = lout
            self._buf_r = rout
            return

        trim = n_windows * window
        lsq = lout[:trim] ** 2
        rsq = rout[:trim] ** 2

        lsum = lsq.reshape(n_windows, window).sum(axis=1)
        rsum = rsq.reshape(n_windows, window).sum(axis=1)

        mean_sq = (lsum + rsum) / window * 0.5 + 1.0e-37
        db = STEPS_PER_DB * 10.0 * np.log10(mean_sq)

        ival = db.astype(np.int64)
        np.clip(ival, 0, self._nbins - 1, out=ival)
        np.add.at(self._hist, ival, 1)

        # 남는 자투리는 다음 feed 로 이월.
        self._buf_l = lout[trim:]
        self._buf_r = rout[trim:]

    def histogram(self) -> np.ndarray:
        """누적 히스토그램(0.01dB 해상도)을 반환한다(Album 누적용)."""
        self._flush()
        return self._hist

    def result(self):
        """누적 히스토그램에서 Track replay gain(dB)을 산출한다.

        충분한 샘플이 없으면 NOT_ENOUGH_SAMPLES 를 반환한다. 곡 끝의 마지막
        불완전 윈도우(_buf 에 남은 자투리)는 일괄 경로와 동일하게 버린다.
        """
        return _gain_from_histogram(self.histogram())

    def peak_normalized(self) -> float:
        """정규화 peak(0~1, 1.0 초과 가능)를 반환한다(track_peak 과 동일 정의)."""
        return self._peak_raw / 32768.0


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

    mp3gain 과 동일한 결과가 되도록 round-half-away-from-zero 방식을 쓴다:
    0 방향으로 자른 뒤 분수부가 0.5 이상이면 절댓값을 1 키운다.
    파이썬 round() 의 banker's rounding 과 0.5 경계에서 어긋나므로 쓰지 않는다.
    """
    raw = db_change / _DB_PER_STEP_DIVISOR
    truncated = int(raw)  # int() 는 0 방향 절단
    frac = abs(raw) - abs(truncated)
    if frac < 0.5:
        return truncated
    return truncated + (-1 if raw < 0 else 1)


def track_peak(left: np.ndarray, right: np.ndarray) -> float:
    """
    한 곡의 정규화 peak(0~1 스케일, 1.0 초과 가능)를 반환한다.

    디코더 출력 원샘플(필터 적용 전)의 좌우 절대 최댓값을 구해 32768.0 으로
    나눈다. decode_pcm 이 좌우 모두 ±32768 스케일로 주므로(mono 도 좌우 복제)
    mp3gain 과 스케일이 정합한다. 채널 수와 무관하게 항상 32768.0 으로 나눠
    mp3gain 과 결과를 일치시킨다.

    샘플이 하나도 없으면 0.0 을 반환한다.

    REPLAYGAIN_TRACK_PEAK 태그 값(정규화)·클리핑 판정의 원천이며,
    게인 산출(라우드니스 dB)에는 영향을 주지 않는다.
    """
    lmax = float(np.abs(left).max()) if left.size else 0.0
    rmax = float(np.abs(right).max()) if right.size else 0.0
    return max(lmax, rmax) / 32768.0