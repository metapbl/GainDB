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
- min/max 스캔 회귀: -s s / -x 등 어느 recalc 경로에서도 global_gain
  min/max 가 0/0 이 아니라 실제 값으로 출력됨(scan_gain 과 대조).

원본 불간섭(11항목): 모든 작업은 tempfile 사본에서만(BaseGainTest).
"""

from __future__ import annotations

import re
from math import log10, floor

from gaindb.tag import read_mp3gain_ape_tag
from gaindb.writer import scan_gain
from gaindb.analysis import db_to_steps
from mp3gain_cli import _auto_clip_track, _auto_clip_album
from tests._support import BaseGainTest


def _find_float(pattern, text):
    m = re.search(pattern, text)
    return float(m.group(1)) if m else None


def _find_int(pattern, text):
    m = re.search(pattern, text)
    return int(m.group(1)) if m else None


def _parse_db_row_minmax(stdout):
    """-o 출력에서 (max_global_gain, min_global_gain) 을 뽑는다.

    -o 기본 행 칸 순서:
      File, MP3 gain, dB gain, Max Amplitude, Max global_gain, Min global_gain
    파일명에 공백이 있어도 뒤 숫자 칸은 안전하므로 뒤에서부터 읽는다
    (Max=[-2], Min=[-1]). 헤더('File\t...')와 "Album" 행은 건너뛰고
    파일 데이터 행 하나를 고른다. 없으면 (None, None).
    """
    for ln in stdout.splitlines():
        if "\t" not in ln:
            continue
        if ln.startswith("File\t"):
            continue
        if ln.startswith('"Album"'):
            continue
        cols = ln.split("\t")
        if len(cols) < 6:
            continue
        try:
            return int(cols[-2]), int(cols[-1])
        except ValueError:
            continue
    return None, None


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


class MinMaxScanRegressionTest(BaseGainTest):
    """global_gain min/max 스캔 회귀 (커밋 d8b44cc).

    버그: min/max 스캔이 MIN_MAX_GAIN_RECALC 비트에만 묶여 있어, 그 비트가
    없는 recalc 경로(-s s 는 FULL 만, -x 는 AMP 만)에서 Max/Min global_gain 이
    0/0 으로 떨어졌다. 원본 mp3gain 은 scanFrameGain 을 어느 recalc 경로에서든
    실행하므로 min/max 는 항상 나온다. 이를 재현·고정한다.

    기대값은 scan_gain(사본)을 직접 불러 동적으로 구한다(fixture 가 ffmpeg 로
    재생성돼도 안 깨지고, scan_gain 은 프레임 파싱만 하는 순수 함수라 신뢰
    가능한 기준이다). CLI -o 출력의 Max/Min 칸이 이 값과 일치하고, 결정적으로
    0/0 이 아님을 확인한다(이 버그의 증상이 정확히 0/0 이었음).

    채널 모드 커버리지를 위해 stereo(mode 0)·mono(mode 3) 변형 fixture 를
    순회한다(둘 다 max global_gain=255 포함). 없으면 SkipTest.
    """

    FIXTURES = ("test_stereo_44k.mp3", "test_mono_44k.mp3")

    def _expected_minmax(self, path):
        """scan_gain 반환을 (min, max) 로 정규화한다.

        mp3gain_cli 는 min_gain, max_gain = scan_gain(path) 순으로 언팩하므로
        (min, max) 튜플을 전제한다. 만약 실제 순서가 반대면 이 한 곳만 뒤집으면
        된다(테스트 전반이 이 헬퍼를 경유).
        """
        a, b = scan_gain(path)
        return a, b  # (min, max)

    def _check(self, opt_args):
        for name in self.FIXTURES:
            with self.subTest(fixture=name):
                path = self.copy_fixture(name)  # 없으면 SkipTest
                exp_min, exp_max = self._expected_minmax(path)

                r = self.run_cli(["-o", *opt_args, path])
                self.assertEqual(r.returncode, 0, msg=r.stderr)

                got_max, got_min = _parse_db_row_minmax(r.stdout)
                self.assertIsNotNone(got_max, "no data row parsed")
                # 회귀 핵심: 0/0 이 아니어야 한다.
                self.assertFalse(got_max == 0 and got_min == 0,
                                 "min/max collapsed to 0/0 (regression)")
                # scan_gain 정답과 일치.
                self.assertEqual(got_max, exp_max,
                                 "CLI max global_gain must match scan_gain")
                self.assertEqual(got_min, exp_min,
                                 "CLI min global_gain must match scan_gain")

    def test_skip_tag_reports_minmax(self):
        # -s s: FULL 만 켜지는 경로. 수정 전엔 0/0 이었음.
        self._check(["-s", "s"])

    def test_maxamponly_reports_minmax(self):
        # -x: AMP 만 켜지는 경로. min/max 는 여전히 나와야 한다.
        self._check(["-x", "-s", "s"])


if __name__ == "__main__":
    import unittest
    unittest.main()
