"""잔여 CLI 분기 통합 테스트 (verify_cli_c1/c2/c3/d1 흡수).

③(분석/태그/클립)이 아직 안 덮은 잔여 분기를 모은다. 전부 원본 mp3gain
동작 재현 검증이다.
- -x maxAmpOnly: dB change==0.000000, maxsample 의미값.
- -d/-m 보정 순서: -d 는 dB 에 선반영(양자화 전), -m 은 스텝에 후반영.
- No changes 분기: -d 로 스텝 0 → "No changes ... are necessary" + 본문 불변.
- -s s(skip_tag): 적용은 되나 APE mp3gain 태그가 생기지 않음.
- 클립 공식 단위: _auto_clip_track/_auto_clip_album 직접 검산.
- -c(ignore_clip_warning): 클립이어도 질의 없이 그대로 적용.
- -s c 상세: 심은 값 그대로 출력(수치 대조), 비파괴(전체 바이트 동일),
  database 11칸.

원본 불간섭(11항목): 모든 작업은 tempfile 사본에서만(BaseGainTest).
"""

from __future__ import annotations

import re
from math import log10, floor

from gaindb.tag import read_mp3gain_ape_tag
from gaindb.analysis import db_to_steps
from mp3gain_cli import _auto_clip_track, _auto_clip_album
from tests._support import BaseGainTest


def _find_float(pattern, text):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def _find_int(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def _read_all_bytes(path):
    with open(path, "rb") as f:
        return f.read()


def _has_ape_mp3gain(path):
    info, _ = read_mp3gain_ape_tag(path)
    return (info.have_track_gain or info.have_track_peak or
            info.have_album_gain or info.have_album_peak or
            info.have_min_max_gain or info.have_album_min_max_gain or
            info.have_undo)


class MaxAmpOnlyTest(BaseGainTest):
    """-x maxAmpOnly: dB=0.000000, maxsample 의미값."""

    def test_x_zero_db_and_maxsample(self):
        path = self.copy_fixture("10cm - 사랑은 은하수 다방에서.mp3")
        r = self.run_cli(["-x", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        db = _find_float(r'"Track" dB change: (-?\d+\.\d+)', r.stdout)
        self.assertEqual(db, 0.0, "maxAmpOnly must report 0 dB change")
        maxpcm = _find_float(
            r"Max PCM sample at current gain: (-?\d+\.\d+)", r.stdout)
        # 48k 곡 peak>1 → maxsample 이 32768 을 넘는 의미값(구체 범위는 느슨히).
        self.assertIsNotNone(maxpcm)
        self.assertGreater(maxpcm, 0.0)


class GainModOrderTest(BaseGainTest):
    """-d/-m 보정 순서: -d 는 dB 선반영, -m 은 스텝 후반영."""

    FIXTURE = "Debussy - Arabesque No.1.mp3"

    def test_d_adds_to_db_before_quantize(self):
        path = self.copy_fixture(self.FIXTURE)
        base = self.run_cli([path]).stdout
        db0 = _find_float(r'"Track" dB change: (-?\d+\.\d+)', base)

        outd = self.run_cli(["-d", "3.0", path]).stdout
        dbd = _find_float(r'"Track" dB change: (-?\d+\.\d+)', outd)
        self.assertIsNotNone(db0)
        self.assertIsNotNone(dbd)
        self.assertLessEqual(abs(dbd - (db0 + 3.0)), 0.001,
                             "-d must add to dB before quantize")

    def test_m_adds_to_steps_after_quantize(self):
        path = self.copy_fixture(self.FIXTURE)
        base = self.run_cli([path]).stdout
        db0 = _find_float(r'"Track" dB change: (-?\d+\.\d+)', base)
        steps0 = _find_int(r'"Track" mp3 gain change: (-?\d+)', base)

        outm = self.run_cli(["-m", "2", path]).stdout
        dbm = _find_float(r'"Track" dB change: (-?\d+\.\d+)', outm)
        stepsm = _find_int(r'"Track" mp3 gain change: (-?\d+)', outm)
        # -m 은 dB 를 바꾸지 않고 스텝만 +2.
        self.assertLessEqual(abs(dbm - db0), 0.001, "-m must not change dB")
        self.assertEqual(stepsm, steps0 + 2, "-m must add to step count")


class NoChangeAndSkipTagTest(BaseGainTest):
    """No changes(스텝 0) + -s s(skip_tag)."""

    FIXTURE = "Debussy - Arabesque No.1.mp3"

    def test_zero_step_no_changes(self):
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)

        # 제안 dB 를 알아내 -d 로 상쇄 → 스텝 0.
        base = self.run_cli([path]).stdout
        db0 = _find_float(r'"Track" dB change: (-?\d+\.\d+)', base)
        self.assertIsNotNone(db0)

        r = self.run_cli(["-r", "-d", f"{-db0}", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("No changes to", r.stdout)
        self.assertIn("are necessary", r.stdout)
        self.assertEqual(before, self.audio_body_sha256(path),
                         "zero-step apply must not change audio")

    def test_skip_tag_writes_no_ape(self):
        path = self.copy_fixture(self.FIXTURE)
        r = self.run_cli(["-r", "-s", "s", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertFalse(_has_ape_mp3gain(path),
                         "-s s must not create an APE mp3gain tag")


class ClipFormulaAndIgnoreTest(BaseGainTest):
    """클립 공식 단위 검산 + -c(경고 무시)."""

    def test_track_clip_formula(self):
        expect = int(floor(4.0 * log10(32767.0 / 30000.0) / log10(2.0)))
        steps, clipped = _auto_clip_track(99, 30000.0)
        self.assertTrue(clipped)
        self.assertEqual(steps, expect)
        # 제안이 상한 이하면 하향 없음.
        steps2, clipped2 = _auto_clip_track(expect, 30000.0)
        self.assertFalse(clipped2)
        self.assertEqual(steps2, expect)

    def test_album_clip_formula(self):
        expect = int(floor(-4.0 * log10(1.2) / log10(2.0)))
        steps, clipped = _auto_clip_album(99, 1.2)
        self.assertTrue(clipped)
        self.assertEqual(steps, expect)

    def test_ignore_clip_applies_without_prompt(self):
        path = self.copy_fixture("10cm - 사랑은 은하수 다방에서.mp3")
        before = self.audio_body_sha256(path)
        # -c: 클립이어도 질의 없이 그대로 적용. stdin 안 줘도 EOFError 안 나야 함.
        r = self.run_cli(["-r", "-c", "-m", "50", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertNotIn("Make change?", r.stderr)
        self.assertIn("Applying mp3 gain change of", r.stdout)
        self.assertNotEqual(before, self.audio_body_sha256(path),
                            "-c must apply the (clipping) gain")


class CheckTagDetailTest(BaseGainTest):
    """-s c 상세: 수치 대조 + 비파괴 + database 11칸."""

    FIXTURE = "Debussy - Arabesque No.1.mp3"

    def test_check_tag_reports_stored_values(self):
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", path]).returncode, 0)

        info, _ = read_mp3gain_ape_tag(path)
        self.assertTrue(info.have_track_gain)

        out = self.run_cli(["-s", "c", path]).stdout
        db = _find_float(r'"Track" dB change: (-?\d+\.\d+)', out)
        step = _find_int(r'"Track" mp3 gain change: (-?\d+)', out)
        maxg = _find_int(r"Max mp3 global gain field: (\d+)", out)
        ming = _find_int(r"Min mp3 global gain field: (\d+)", out)

        self.assertIsNotNone(db)
        self.assertLessEqual(abs(db - info.track_gain), 1e-4,
                             "printed dB must equal stored track_gain")
        self.assertEqual(step, db_to_steps(info.track_gain),
                         "printed step must equal db_to_steps(track_gain)")
        self.assertEqual(maxg, info.max_gain)
        self.assertEqual(ming, info.min_gain)

    def test_check_tag_is_nondestructive(self):
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", path]).returncode, 0)
        before = _read_all_bytes(path)   # -s c 는 아무것도 안 쓰므로 전체 동일.
        self.run_cli(["-s", "c", path])
        after = _read_all_bytes(path)
        self.assertEqual(before, after,
                         "-s c must not modify the file at all")

    def test_check_tag_database_11_columns(self):
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", path]).returncode, 0)

        out = self.run_cli(["-o", "-s", "c", path]).stdout
        data = next((ln for ln in out.splitlines()
                     if "\t" in ln and not ln.startswith("File\t")), None)
        self.assertIsNotNone(data, "database data row missing")
        cols = data.split("\t")
        self.assertEqual(len(cols), 11, f"expected 11 columns, got {len(cols)}")
        # track gain 있음 → col1/col2 채워짐. 단일 -r 이라 album 은 NA.
        self.assertNotEqual(cols[1], "NA")
        self.assertNotEqual(cols[2], "NA")
        self.assertEqual(cols[6], "NA")
        self.assertEqual(cols[7], "NA")


if __name__ == "__main__":
    import unittest
    unittest.main()
