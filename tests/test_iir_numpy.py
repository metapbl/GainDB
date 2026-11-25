# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""numpy 블록 IIR(analysis._iir) 검증 (1.5, D118~D121).

1) scipy 대조: 9개 샘플레이트 계수에서 출력·최종 상태가 scipy.signal.lfilter 와
   같다(상대 1e-9). scipy 는 개발 의존성(requirements-dev.txt)이라 없으면 skip.
2) 청크 불변: TrackAnalyzer 에 어떤 크기로 잘라 먹여도 히스토그램이 통짜와
   np.array_equal (D010·D120). scipy 불필요.
3) fixture 대조: 모든 fixture 에서 게인·적용 스텝이 scipy lfilter 기준과
   정확히 같다 (D121). 기준 히스토그램은 이 파일이 scipy 로 따로 계산한다.
"""

from __future__ import annotations

import unittest

import numpy as np

from tests._support import BaseGainTest, available_fixtures

from gaindb import analysis
from gaindb.analysis import TrackAnalyzer, analyze_track, db_to_steps, track_histogram
from gaindb.decode import DecodeError, decode_pcm

try:
    from scipy.signal import lfilter
except ImportError:  # 실행 환경(requirements.txt)에는 scipy 가 없다
    lfilter = None

needs_scipy = unittest.skipIf(lfilter is None, "scipy not installed (dev dependency)")


def _signal(n: int, seed: int) -> np.ndarray:
    """음량이 천천히 바뀌는 ±32768 스케일 잡음."""
    rng = np.random.default_rng(seed)
    env = 1.0 + np.sin(np.arange(n) / 3000.0)
    return rng.standard_normal(n) * 4000.0 * env


def _ref_histogram(left, right, sr) -> np.ndarray:
    """scipy lfilter 로 계산한 기준 히스토그램(ReplayGain 사양대로 독립 구현)."""
    yb, ya, bb, ba = analysis._FILTER_COEFFS[sr]
    lo = lfilter(bb, ba, lfilter(yb, ya, left))
    ro = lfilter(bb, ba, lfilter(yb, ya, right))
    window = int(np.ceil(sr * analysis.RMS_WINDOW_MS / 1000.0))
    nw = lo.size // window
    nbins = analysis.STEPS_PER_DB * analysis.MAX_DB
    hist = np.zeros(nbins, dtype=np.int64)
    if nw == 0:
        return hist
    ls = (lo[: nw * window] ** 2).reshape(nw, window).sum(axis=1)
    rs = (ro[: nw * window] ** 2).reshape(nw, window).sum(axis=1)
    db = analysis.STEPS_PER_DB * 10.0 * np.log10((ls + rs) / window * 0.5 + 1.0e-37)
    np.add.at(hist, np.clip(db.astype(np.int64), 0, nbins - 1), 1)
    return hist


@needs_scipy
class IirMatchesScipyTest(unittest.TestCase):
    def test_output_and_state_match_lfilter_cascade(self):
        L = analysis._IIR_BLOCK
        for sr, (yb, ya, bb, ba) in sorted(analysis._FILTER_COEFFS.items()):
            ny, nbw = len(ya) - 1, len(ba) - 1
            zi = np.tile(np.linspace(-50.0, 50.0, ny + nbw), (2, 1))
            zi[1] *= -0.5
            y0, z0 = analysis._iir(sr, np.zeros((2, 0)), zi)  # 빈 입력: 상태 그대로
            self.assertEqual(y0.shape, (2, 0))
            self.assertTrue(np.array_equal(z0, zi))
            # n=0 은 scipy 가 초기화 안 된 zf 를 돌려줘 기준으로 못 쓴다
            U = L * analysis._IIR_GROUP  # 그룹 길이
            for n in (1, L - 1, L, L + 1, 3 * L + 123, U - 1, U, U + 1, 3 * U + 123):
                with self.subTest(sr=sr, n=n):
                    x = np.stack((_signal(n, seed=n + sr), _signal(n, seed=n + sr + 1)))
                    y, z = analysis._iir(sr, x, zi)
                    for c in range(2):
                        u, zu = lfilter(yb, ya, x[c], zi=zi[c, :ny])
                        ref_y, zb = lfilter(bb, ba, u, zi=zi[c, ny:])
                        scale = max(float(np.abs(ref_y).max()), 1.0)
                        self.assertLessEqual(float(np.abs(y[c] - ref_y).max()), 1e-9 * scale)
                        ref_z = np.concatenate((zu, zb))
                        self.assertLessEqual(float(np.abs(z[c] - ref_z).max()), 1e-9 * scale)


class ChunkInvarianceTest(unittest.TestCase):
    def test_histogram_equal_for_any_chunking(self):
        L = analysis._IIR_BLOCK
        for sr in (44100, 8000):
            n = sr * 2 + 77
            left, right = _signal(n, 1), _signal(n, 2) * 0.5
            batch = track_histogram(left, right, sr)
            U = L * analysis._IIR_GROUP
            for chunk in (1, L - 1, L + 1, U - 1, U, U + 1, 997, 2205, n):
                if chunk == 1:  # 1샘플 청크는 느려서 앞부분만
                    m = sr // 4
                    l1, r1 = left[:m], right[:m]
                    want = track_histogram(l1, r1, sr)
                else:
                    l1, r1, want = left, right, batch
                with self.subTest(sr=sr, chunk=chunk):
                    an = TrackAnalyzer(sr)
                    for s in range(0, l1.size, chunk):
                        an.feed(l1[s:s + chunk], r1[s:s + chunk])
                    self.assertTrue(np.array_equal(an.histogram(), want))
                    self.assertEqual(an.result(), analysis._gain_from_histogram(want))


@needs_scipy
class FixtureParityTest(BaseGainTest):
    def test_gain_and_steps_match_scipy_reference(self):
        names = [p.name for p in available_fixtures()]
        if not names:
            raise unittest.SkipTest("no test fixtures available")
        for name in names:
            with self.subTest(fixture=name):
                try:
                    left, right, sr = decode_pcm(self.copy_fixture(name))
                except DecodeError as exc:
                    raise unittest.SkipTest(f"decode unavailable: {exc}")
                if sr not in analysis._FILTER_COEFFS:
                    continue
                ref = analysis._gain_from_histogram(_ref_histogram(left, right, sr))
                got = analyze_track(left, right, sr)
                self.assertEqual(got, ref)
                an = TrackAnalyzer(sr)
                for s in range(0, left.size, 4096):
                    an.feed(left[s:s + 4096], right[s:s + 4096])
                self.assertEqual(an.result(), ref)
                if ref is not analysis.NOT_ENOUGH_SAMPLES:
                    self.assertEqual(db_to_steps(got), db_to_steps(ref))


if __name__ == "__main__":
    unittest.main()
