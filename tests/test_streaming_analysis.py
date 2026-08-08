# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""TrackAnalyzer 스트리밍 분석 = 통짜 분석 동일성 테스트.

진척 로그(10.2)의 "스트리밍 결과는 통짜 처리와 비트 단위 동일(diff=0)"을
정식 테스트로 고정한다. 스트리밍 경로(TrackAnalyzer.feed 누적)가 통짜 경로
(analyze_track / track_peak / track_histogram)와 같은 결과를 내는지 확인한다.

두 층위로 검증한다:
  1) in-memory 청크 분할(주 검증): decode_pcm 으로 한 번만 디코딩한 배열을
     여러 청크 크기로 잘라 TrackAnalyzer.feed 에 먹인다. ffmpeg 를 한 번만
     부르므로 "같은 PCM" 이 보장되어, 순수하게 스트리밍 알고리즘(lfilter zi
     이어받기 + 윈도우 자투리 이월 + peak 갱신)만 검증한다. 청크 크기를 일부러
     50ms 윈도우의 비배수로 골라 자투리 이월 경로를 강하게 탄다.
  2) end-to-end(보조 검증): 실제 decode_pcm_streaming 파이프라인을 태워
     (ffmpeg 재호출) 통짜와 일치하는지 한 번 확인한다. ffmpeg 디코딩이
     결정론적이라는 가정 하에 두 디코딩 결과가 같고, 그 위에서 알고리즘도
     같으므로 최종 결과가 일치해야 한다.

동일성 기준: 히스토그램이 같으면 gain·나머지가 자동으로 같으므로 히스토그램을
np.array_equal 로(정수 카운트라 완전 일치) 대조하는 것이 가장 근본적이다.
gain(dB)·peak 도 함께 확인한다. gain 은 히스토그램에서 유도되므로 정수 경계가
같으면 완전히 같아야 하나, 부동소수 재현이 청크 크기에 따라 흔들릴 가능성을
감안해 우선 assertEqual 로 엄격히 시도한다.

원본 불간섭: BaseGainTest 를 상속해 copy_fixture 로 사본에서만 디코딩한다
(읽기 전용이라 파괴적이진 않으나 관례 통일 + FixtureGuard 안전망). ffmpeg
부재 시 decode 가 DecodeError 를 던지므로 SkipTest 로 전환한다.
"""

from __future__ import annotations

import unittest

import numpy as np

from tests._support import BaseGainTest, available_fixtures, KNOWN_FIXTURES

from gaindb.decode import decode_pcm, decode_pcm_streaming, DecodeError
from gaindb.analysis import (
    TrackAnalyzer,
    analyze_track,
    track_peak,
    track_histogram,
)


def _feed_in_chunks(analyzer: TrackAnalyzer,
                    left: np.ndarray, right: np.ndarray,
                    chunk: int) -> None:
    """left/right 를 chunk 샘플씩 잘라 analyzer 에 순차로 먹인다.

    슬라이스는 원본 배열의 view 이지만 feed 는 읽기만 하므로 안전하다. 마지막
    조각은 chunk 보다 짧을 수 있다(그대로 넘긴다).
    """
    n = left.size
    start = 0
    while start < n:
        end = min(start + chunk, n)
        analyzer.feed(left[start:end], right[start:end])
        start = end


class StreamingEqualityTest(BaseGainTest):
    """스트리밍 누적 결과가 통짜 결과와 동일한지 확인한다."""

    # 대표 fixture 하나로 여러 청크 크기를 훑는다(전 fixture 를 다 돌면 느리다).
    # available_fixtures 에서 실제 존재하는 첫 번째를 고른다.
    def _pick_fixture_name(self) -> str:
        avail = available_fixtures()
        if not avail:
            raise unittest.SkipTest("no test fixtures available")
        return avail[0].name

    def _decode_copy(self, name: str):
        """사본을 디코딩해 (left, right, sr) 반환. ffmpeg 없으면 SkipTest."""
        path = self.copy_fixture(name)
        try:
            return decode_pcm(path)
        except DecodeError as exc:
            raise unittest.SkipTest(f"decode unavailable: {exc}")

    def test_histogram_matches_across_chunk_sizes(self):
        """여러 청크 크기에서 스트리밍 히스토그램이 통짜와 완전히 같다.

        청크 크기는 50ms 윈도우(예: 44.1k → 2205 샘플)의 비배수를 포함해,
        매 청크가 윈도우 중간에서 끊겨 자투리 이월 경로를 타게 한다. 작은
        비배수(101)로 자투리 이월을 촘촘히 검증하되, 아주 작은 청크(1·7 등)는
        같은 경로를 수백만 번 반복할 뿐 새 경로를 열지 않으면서 극단적으로
        느려 제외한다.
        """
        name = self._pick_fixture_name()
        left, right, sr = self._decode_copy(name)

        batch_hist = track_histogram(left, right, sr)

        # 작은 비배수(자투리 이월) + 윈도우 비배수 + 큰 청크 + 통짜.
        for chunk in (101, 999, 4096, 44101, left.size):
            if chunk <= 0:
                continue
            with self.subTest(chunk=chunk):
                an = TrackAnalyzer(sr)
                _feed_in_chunks(an, left, right, chunk)
                self.assertTrue(
                    np.array_equal(an.histogram(), batch_hist),
                    f"histogram mismatch at chunk={chunk} for {name}",
                )

    def test_gain_matches(self):
        """스트리밍 result(dB)가 통짜 analyze_track 과 같다(히스토그램 동일 → 동일)."""
        name = self._pick_fixture_name()
        left, right, sr = self._decode_copy(name)

        batch_gain = analyze_track(left, right, sr)

        an = TrackAnalyzer(sr)
        _feed_in_chunks(an, left, right, 999)  # 윈도우 비배수
        stream_gain = an.result()

        # 히스토그램이 같으면 gain 도 완전히 같아야 한다.
        self.assertEqual(stream_gain, batch_gain)

    def test_peak_matches(self):
        """스트리밍 peak_normalized 가 통짜 track_peak 과 같다(필터 전 원샘플 기준)."""
        name = self._pick_fixture_name()
        left, right, sr = self._decode_copy(name)

        batch_peak = track_peak(left, right)

        an = TrackAnalyzer(sr)
        _feed_in_chunks(an, left, right, 999)
        self.assertEqual(an.peak_normalized(), batch_peak)

    def test_single_chunk_equals_batch(self):
        """청크 하나(전체를 한 번에)로 먹여도 통짜와 같다(자투리 경로 배제 대조)."""
        name = self._pick_fixture_name()
        left, right, sr = self._decode_copy(name)

        batch_hist = track_histogram(left, right, sr)
        an = TrackAnalyzer(sr)
        an.feed(left, right)  # 통짜 한 방
        self.assertTrue(np.array_equal(an.histogram(), batch_hist))

    def test_end_to_end_streaming_pipeline(self):
        """실제 decode_pcm_streaming 파이프라인이 통짜와 일치한다(ffmpeg 재호출).

        ffmpeg 디코딩이 결정론적이라는 가정 하에, 스트리밍 디코드→feed 누적
        결과가 통짜 디코드→analyze_track 과 같아야 한다. in-memory 대조가
        알고리즘을, 이 테스트가 실제 파이프라인을 커버한다.
        """
        name = self._pick_fixture_name()

        # 통짜 경로.
        batch_left, batch_right, sr = self._decode_copy(name)
        batch_gain = analyze_track(batch_left, batch_right, sr)
        batch_peak = track_peak(batch_left, batch_right)

        # 스트리밍 경로(별도 사본, 실제 decode_pcm_streaming).
        stream_path = self.copy_fixture(name)
        an = TrackAnalyzer(sr)
        try:
            stream_sr = decode_pcm_streaming(stream_path, on_chunk=an.feed)
        except DecodeError as exc:
            raise unittest.SkipTest(f"decode unavailable: {exc}")

        self.assertEqual(stream_sr, sr)
        self.assertEqual(an.result(), batch_gain)
        self.assertEqual(an.peak_normalized(), batch_peak)


class StreamingMultiRateTest(BaseGainTest):
    """여러 샘플레이트 fixture 에서 스트리밍=통짜 히스토그램 동일성 스팟 체크.

    청크 하나는 윈도우 비배수(1000)로 고정하고, 존재하는 여러 fixture 를 돌며
    샘플레이트별로 자투리 이월·zi 이어받기가 정상인지 확인한다. 전 fixture 를
    돌되 각 fixture 당 청크 크기는 하나만 써서 시간을 아낀다.
    """

    def test_multi_rate_histogram_equality(self):
        avail = available_fixtures()
        if not avail:
            raise unittest.SkipTest("no test fixtures available")

        tested = 0
        for p in avail:
            with self.subTest(fixture=p.name):
                dst = self.copy_fixture(p.name)
                try:
                    left, right, sr = decode_pcm(dst)
                except DecodeError as exc:
                    raise unittest.SkipTest(f"decode unavailable: {exc}")

                batch_hist = track_histogram(left, right, sr)
                an = TrackAnalyzer(sr)
                _feed_in_chunks(an, left, right, 1000)  # 윈도우 비배수
                self.assertTrue(
                    np.array_equal(an.histogram(), batch_hist),
                    f"histogram mismatch for {p.name} (sr={sr})",
                )
                tested += 1

        if tested == 0:
            raise unittest.SkipTest("no fixtures decoded")


if __name__ == "__main__":
    unittest.main()
