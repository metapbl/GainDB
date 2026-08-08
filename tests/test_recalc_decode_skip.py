# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""D-2 recalc 디코딩 스킵 통합 테스트 (in-process).

이 파일은 decode_pcm 호출 "횟수"를 측정해야 하므로, 다른 통합 테스트와 달리
CLI 를 subprocess 가 아닌 in-process(gaindb_cli.main 직접 호출)로 돌리고
gaindb_cli.decode_pcm 을 가로챈다(subprocess 로는 monkeypatch 불가).

fixture 불간섭(9항)은 BaseGainTest 의 tempfile 사본 + FixtureGuard 로 지킨다.
run_cli(subprocess) 대신 _run_inproc 를 쓴다.

검증(mp3gain 과 동일한 동작):
- recalc 비트마스크(FULL/AMP/MIN_MAX)의 결과인 디코딩 스킵 — 디코더 예외
  (2.1)의 직접적 귀결. 태그 완비 파일 재분석은 decode_pcm 을 부르지 않는다.
- -s u(force_update): dirty 만 강제, have_* 유지 → recalc==0 → decode 스킵.
- -s r(force_recalc): have_* 끄고 재계산(undo 보존) → decode 호출.
- update file tags: 순수 분석 경로에서 dirty 곡의 태그 기록.
- 선행읽기 구조 회귀: -g → -u 오디오 본문 복원.
"""

from __future__ import annotations

import io
from contextlib import redirect_stdout, redirect_stderr

import gaindb_cli
from gaindb.tag import read_mp3gain_tags
from tests._support import BaseGainTest


class _DecodeCounter:
    """gaindb_cli.decode_pcm 을 가로채 호출 횟수를 센다."""

    def __init__(self):
        self.count = 0
        self._orig = None

    def __enter__(self):
        self._orig = gaindb_cli.decode_pcm

        def counting(path):
            self.count += 1
            return self._orig(path)

        gaindb_cli.decode_pcm = counting
        return self

    def __exit__(self, *exc):
        gaindb_cli.decode_pcm = self._orig
        return False


class RecalcDecodeSkipTest(BaseGainTest):
    """in-process CLI 호출 + decode_pcm 카운트. (subprocess 미사용)"""

    def _run_inproc(self, args):
        """gaindb_cli.main(["gaindb_cli.py", *args]) 를 in-process 호출.

        stdout/stderr 를 캡처해 (rc, out, err) 반환. fixture 불간섭은 상위
        BaseGainTest 의 tempfile 사본 + tearDown FixtureGuard 로 보장된다.
        """
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = gaindb_cli.main(["gaindb_cli.py", *[str(a) for a in args]])
        return rc, out.getvalue(), err.getvalue()

    def _audio_body(self, path):
        # tag_offset 이전 오디오 본문 바이트(태그 유무와 무관 비교용).
        info, ft = read_mp3gain_tags(path, False)
        with open(path, "rb") as f:
            return f.read(ft.tag_offset)

    # -- 태그 완비 재분석 → decode 스킵 -------------------------------------
    def test_full_tags_skip_decode_on_reanalysis(self):
        f = self.copy_fixture("test_gain_44k.mp3")

        # 1차 순수 분석: 디코딩 발생 + 태그 완비(update file tags 로 기록).
        with _DecodeCounter() as dc1:
            rc, _o, _e = self._run_inproc([f])
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(dc1.count, 1, "first analysis must decode")

        info1, _ = read_mp3gain_tags(f, False)
        self.assertTrue(info1.have_track_gain and info1.have_track_peak
                        and info1.have_min_max_gain,
                        "first analysis must fill track tags")

        # 2차 재분석: recalc==0 → decode_pcm 미호출.
        with _DecodeCounter() as dc2:
            rc, _o, _e = self._run_inproc([f])
        self.assertEqual(rc, 0)
        self.assertEqual(dc2.count, 0,
                         "re-analysis on complete tags must not decode")

    # -- -s u: dirty 강제하되 decode 스킵 -----------------------------------
    def test_force_update_no_decode(self):
        f = self.copy_fixture("test_gain_44k.mp3")
        # 태그 완비 상태로 만든다.
        self._run_inproc([f])

        with _DecodeCounter() as dc:
            rc, _o, _e = self._run_inproc(["-s", "u", f])
        self.assertEqual(rc, 0)
        self.assertEqual(dc.count, 0,
                         "-s u on complete tags must not decode")

        info, _ = read_mp3gain_tags(f, False)
        self.assertTrue(info.have_track_gain and info.have_track_peak,
                        "-s u must preserve track tags")

    # -- -s r: 재계산 → decode 호출 + undo 보존 -----------------------------
    def test_force_recalc_decodes_and_preserves_undo(self):
        f = self.copy_fixture("test_gain_48k.mp3")
        # -r 로 적용(undo 가 생기도록).
        self._run_inproc(["-r", f])
        pre, _ = read_mp3gain_tags(f, False)
        self.assertTrue(pre.have_undo, "precondition: undo present")
        undo_l, undo_r = pre.undo_left, pre.undo_right

        with _DecodeCounter() as dc:
            rc, _o, _e = self._run_inproc(["-s", "r", f])
        self.assertEqual(rc, 0)
        self.assertGreaterEqual(dc.count, 1, "-s r must recalc (decode)")

        post, _ = read_mp3gain_tags(f, False)
        self.assertTrue(post.have_track_gain, "-s r must refill track gain")
        # undo 는 보존되어야 한다.
        self.assertTrue(post.have_undo
                        and post.undo_left == undo_l
                        and post.undo_right == undo_r,
                        "-s r must preserve undo")

    # -- update file tags: 순수 분석 경로에서 dirty 곡 태그 기록 --------------
    def test_pure_analysis_writes_dirty_tags(self):
        f = self.copy_fixture("test_gain_44k.mp3")
        none_info, _ = read_mp3gain_tags(f, False)
        self.assertFalse(none_info.have_track_gain,
                         "fresh copy must have no track gain")

        self._run_inproc([f])  # 순수 분석
        after, _ = read_mp3gain_tags(f, False)
        self.assertTrue(after.have_track_gain,
                        "pure analysis must write dirty track tag")

    # -- 선행읽기 회귀: -g → -u 본문 복원 -----------------------------------
    def test_direct_gain_undo_roundtrip_inproc(self):
        f = self.copy_fixture("test_gain_44k.mp3")
        before = self._audio_body(f)

        # 음수 스텝 먼저(-g -3) → -u 복원(255 상한 회피, 9항).
        self._run_inproc(["-g", "-3", f])
        self.assertNotEqual(before, self._audio_body(f),
                            "-g -3 must change audio body")

        self._run_inproc(["-u", f])
        self.assertEqual(before, self._audio_body(f),
                         "-u must restore audio body")


if __name__ == "__main__":
    import unittest
    unittest.main()