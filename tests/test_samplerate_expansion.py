"""6단계 샘플레이트 확장 검증 (32k / MPEG2·MPEG2.5).

세 부류:
  1) FrameParseTest      — parse_file 이 각 fixture 의 버전·샘플레이트·채널·
                           global_gain 을 사양대로 읽는지(0/0 아님, 정상 범위).
  2) LowRateRoundTripTest — 각 fixture 에 -g -3 → +3 적용 시 오디오 본문이
                           비트 동일로 복원되는지(writer.py 의 MPEG2/2.5 경로).
  3) LowRateAnalysisTest — decode_pcm+analyze_track 이 각 샘플레이트에서
                           예외 없이 유한 dB 를 내는지(계수 테이블 실동작).

mp3gain 과의 dB 정답 대조는 통합 스위트 밖(manual_checks/
compare_exe_lowrate.py, git 제외)에서 수동 수행한다 — 외부 exe 의존을
통합 스위트에 넣지 않기 위함(mutagen 사례와 동일 방침).

모든 fixture 는 git 제외 변형이라 부재 시 각 테스트가 SkipTest 로 건너뛴다.
round-trip 은 음수 스텝 먼저(-3)로 한다: 이 fixture 들은 max global_gain=255
(상한)라 +N 을 먼저 하면 255 클램프로 비가역이 되기 때문(9항).
min 은 128~144 라 하한(0)·0-gain 클램프에서 멀어 -3 은 안전하다.
"""

from __future__ import annotations

import math
import unittest

from tests._support import BaseGainTest

# fixture → (기대 mpegver, 기대 samplerate_hz, 기대 nchan, granule 수)
# mpegver: 3=MPEG1, 2=MPEG2, 0=MPEG2.5 (frame.py 규약)
# granule: MPEG1=2, MPEG2/2.5=1  → gains 개수 = frames * granule * nchan
_FIXTURE_META = {
    "test_32k.mp3":      (3, 32000, 2, 2),
    "test_24k.mp3":      (2, 24000, 2, 1),
    "test_22k.mp3":      (2, 22050, 2, 1),
    "test_16k.mp3":      (2, 16000, 2, 1),
    "test_12k.mp3":      (0, 12000, 2, 1),
    "test_11k.mp3":      (0, 11025, 2, 1),
    "test_8k.mp3":       (0,  8000, 2, 1),
    "test_mono_24k.mp3": (2, 24000, 1, 1),
    "test_mono_12k.mp3": (0, 12000, 1, 1),
}


class FrameParseTest(BaseGainTest):
    """parse_file 이 MPEG1/2/2.5 사이드 정보를 사양대로 읽는지."""

    def _check_parse(self, name, exp_ver, exp_sr, exp_nch, granule):
        from gaindb.frame import parse_file
        copy = self.copy_fixture(name)
        frames = list(parse_file(copy))
        self.assertGreater(len(frames), 0, f"{name}: no frames parsed")

        first = frames[0]
        self.assertEqual(first.mpegver, exp_ver,
                         f"{name}: mpegver {first.mpegver} != {exp_ver}")
        self.assertEqual(first.samplerate_hz, exp_sr,
                         f"{name}: samplerate {first.samplerate_hz} != {exp_sr}")
        self.assertEqual(first.nchan, exp_nch,
                         f"{name}: nchan {first.nchan} != {exp_nch}")

        # gains 개수 = frames * granule * nchan
        all_gains = [g for fr in frames for g in fr.gains]
        expected_count = len(frames) * granule * exp_nch
        self.assertEqual(len(all_gains), expected_count,
                         f"{name}: gains count {len(all_gains)} != {expected_count}")

        # global_gain 은 8비트라 0..255. 실제 음원은 0/0 이 아니어야 한다.
        gmin, gmax = min(all_gains), max(all_gains)
        self.assertGreaterEqual(gmin, 0)
        self.assertLessEqual(gmax, 255)
        self.assertNotEqual((gmin, gmax), (0, 0),
                            f"{name}: gains all zero (side-info offset wrong?)")

    def test_parse_32k(self):
        self._check_parse("test_32k.mp3", *_FIXTURE_META["test_32k.mp3"])

    def test_parse_24k(self):
        self._check_parse("test_24k.mp3", *_FIXTURE_META["test_24k.mp3"])

    def test_parse_22k(self):
        self._check_parse("test_22k.mp3", *_FIXTURE_META["test_22k.mp3"])

    def test_parse_16k(self):
        self._check_parse("test_16k.mp3", *_FIXTURE_META["test_16k.mp3"])

    def test_parse_12k(self):
        self._check_parse("test_12k.mp3", *_FIXTURE_META["test_12k.mp3"])

    def test_parse_11k(self):
        self._check_parse("test_11k.mp3", *_FIXTURE_META["test_11k.mp3"])

    def test_parse_8k(self):
        self._check_parse("test_8k.mp3", *_FIXTURE_META["test_8k.mp3"])

    def test_parse_mono_24k(self):
        self._check_parse("test_mono_24k.mp3", *_FIXTURE_META["test_mono_24k.mp3"])

    def test_parse_mono_12k(self):
        self._check_parse("test_mono_12k.mp3", *_FIXTURE_META["test_mono_12k.mp3"])


class LowRateRoundTripTest(BaseGainTest):
    """-g -3 → +3 로 오디오 본문이 비트 동일 복원되는지(MPEG2/2.5 쓰기 경로)."""

    def _assert_roundtrip(self, name):
        copy = self.copy_fixture(name)
        before = self.audio_body_sha256(copy)

        r1 = self.run_cli(["-g", "-3", copy])
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        self.assertNotEqual(before, self.audio_body_sha256(copy),
                            f"{name}: gain apply did not change audio body")

        r2 = self.run_cli(["-g", "3", copy])
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        self.assertEqual(before, self.audio_body_sha256(copy),
                         f"{name}: -3/+3 did not round-trip bit-for-bit")

    def test_roundtrip_32k(self):
        self._assert_roundtrip("test_32k.mp3")

    def test_roundtrip_24k(self):
        self._assert_roundtrip("test_24k.mp3")

    def test_roundtrip_16k(self):
        self._assert_roundtrip("test_16k.mp3")

    def test_roundtrip_8k(self):
        self._assert_roundtrip("test_8k.mp3")

    def test_roundtrip_mono_24k(self):
        self._assert_roundtrip("test_mono_24k.mp3")

    def test_roundtrip_mono_12k(self):
        self._assert_roundtrip("test_mono_12k.mp3")


class LowRateAnalysisTest(BaseGainTest):
    """decode_pcm + analyze_track 이 각 샘플레이트에서 유한 dB 를 내는지.

    계수 테이블이 실제로 해당 샘플레이트에서 동작함을 통합 스위트 안에서 보장.
    dB 정답 대조는 manual_checks/compare_exe_lowrate.py 참조.
    """

    def _check_analysis(self, name):
        from gaindb.decode import decode_pcm
        from gaindb.analysis import analyze_track, NOT_ENOUGH_SAMPLES
        copy = self.copy_fixture(name)
        left, right, sr = decode_pcm(copy)
        db = analyze_track(left, right, sr)
        self.assertIsNot(db, NOT_ENOUGH_SAMPLES,
                         f"{name}: not enough samples (decode/analyze failed)")
        self.assertTrue(math.isfinite(db),
                        f"{name}: analyze_track returned non-finite {db}")
        # 음악 트랙의 replay gain 은 상식적으로 -30..+30 dB 안에 든다.
        self.assertGreater(db, -30.0, f"{name}: implausible dB {db}")
        self.assertLess(db, 30.0, f"{name}: implausible dB {db}")

    def test_analysis_32k(self):
        self._check_analysis("test_32k.mp3")

    def test_analysis_24k(self):
        self._check_analysis("test_24k.mp3")

    def test_analysis_22k(self):
        self._check_analysis("test_22k.mp3")

    def test_analysis_16k(self):
        self._check_analysis("test_16k.mp3")

    def test_analysis_12k(self):
        self._check_analysis("test_12k.mp3")

    def test_analysis_11k(self):
        self._check_analysis("test_11k.mp3")

    def test_analysis_8k(self):
        self._check_analysis("test_8k.mp3")

    def test_analysis_mono_24k(self):
        self._check_analysis("test_mono_24k.mp3")

    def test_analysis_mono_12k(self):
        self._check_analysis("test_mono_12k.mp3")


if __name__ == "__main__":
    unittest.main()