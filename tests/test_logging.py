"""tests/test_logging.py — gui/logging.py 순수 함수 검증(원본 음원·ffmpeg·Qt 불요).

로그 형식·활성 판정(enabled+path)·append 누적·쓰기가능 검사·dB 반올림(정밀값)을
임시 파일에서만 검증한다(원본 음원 불간섭). 원본 LogErr/LogRadioAnalysis/
LogAlbumAnalysis/LogChange 의 출력 형식과 우리 확정 정책(정밀값·ISO 타임스탬프·
enabled/path 분리 A안)이 유지되는지 회귀 고정한다.
"""

import os
import re
import tempfile
import unittest

from gui.logging import (
    LogConfig, FIVELOG10TWO,
    log_error, log_analysis_track, log_analysis_album, log_change,
    check_writable,
)

# ISO 8601 타임스탬프(YYYY-MM-DD HH:MM:SS) 접두 패턴.
_TS = re.compile(r"^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\t")


def _read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


class LoggingTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="gaindb_log_")
        self.err = os.path.join(self.tmp, "err.log")
        self.ana = os.path.join(self.tmp, "ana.log")
        self.chg = os.path.join(self.tmp, "chg.log")

    def tearDown(self):
        for name in os.listdir(self.tmp):
            os.remove(os.path.join(self.tmp, name))
        os.rmdir(self.tmp)

    # --- 활성 판정(enabled + path, A안) ---

    def test_disabled_is_noop(self):
        """enabled=False 면 경로가 있어도 파일을 만들지 않는다."""
        cfg = LogConfig(error_enabled=False, error_path=self.err)
        log_error(cfg, "boom")
        self.assertFalse(os.path.exists(self.err))

    def test_enabled_without_path_is_noop(self):
        """enabled=True 라도 경로가 비면 no-op(체크만 하고 경로 안 넣은 경우)."""
        cfg = LogConfig(error_enabled=True, error_path="")
        log_error(cfg, "boom")  # 예외 없이 조용히 넘어가야 함

    def test_active_flags(self):
        cfg = LogConfig(error_enabled=True, error_path=self.err)
        self.assertTrue(cfg.error_active())
        cfg.error_path = ""
        self.assertFalse(cfg.error_active())
        cfg.error_path = self.err
        cfg.error_enabled = False
        self.assertFalse(cfg.error_active())

    # --- Error Log ---

    def test_error_format_and_append(self):
        cfg = LogConfig(error_enabled=True, error_path=self.err)
        log_error(cfg, "first error")
        log_error(cfg, "second error")
        lines = _read(self.err).splitlines()
        self.assertEqual(len(lines), 2)  # append 누적
        self.assertRegex(lines[0], _TS)
        self.assertTrue(lines[0].endswith("\tfirst error"))
        self.assertTrue(lines[1].endswith("\tsecond error"))

    # --- Analysis Log(Track / Album) ---

    def test_analysis_track_format(self):
        cfg = LogConfig(analysis_enabled=True, analysis_path=self.ana)
        log_analysis_track(cfg, "C:\\music\\a.mp3", -6.5, 17196.4)
        line = _read(self.ana).splitlines()[0]
        self.assertRegex(line, _TS)
        # ts<TAB>path<TAB>TrackdB: <db><TAB>MaxAmp: <int>
        parts = line.split("\t")
        self.assertEqual(parts[1], "C:\\music\\a.mp3")
        self.assertEqual(parts[2], "TrackdB: -6.5")
        self.assertEqual(parts[3], "MaxAmp: 17196")  # 반올림 정수

    def test_analysis_album_format(self):
        cfg = LogConfig(analysis_enabled=True, analysis_path=self.ana)
        log_analysis_album(cfg, "C:\\music\\Album1", -8.0)
        line = _read(self.ana).splitlines()[0]
        parts = line.split("\t")
        self.assertEqual(parts[1], "C:\\music\\Album1")
        self.assertEqual(parts[2], "AlbumdB: -8.0")

    # --- Change Log(정밀값 dB, steps==0 no-op) ---

    def test_change_precise_db(self):
        cfg = LogConfig(change_enabled=True, change_path=self.chg)
        log_change(cfg, "C:\\music\\a.mp3", 3)
        line = _read(self.chg).splitlines()[0]
        parts = line.split("\t")
        self.assertEqual(parts[1], "C:\\music\\a.mp3")
        # 3 * 5log10(2) = 4.515... -> 소수 첫째자리 4.5
        expected = format(3 * FIVELOG10TWO, ".1f")
        self.assertEqual(parts[2], expected)
        self.assertEqual(parts[2], "4.5")

    def test_change_negative_steps(self):
        cfg = LogConfig(change_enabled=True, change_path=self.chg)
        log_change(cfg, "C:\\music\\a.mp3", -3)
        line = _read(self.chg).splitlines()[0]
        self.assertEqual(line.split("\t")[2], format(-3 * FIVELOG10TWO, ".1f"))

    def test_change_zero_steps_is_noop(self):
        """steps==0 은 실질 변경 없음이라 기록하지 않는다."""
        cfg = LogConfig(change_enabled=True, change_path=self.chg)
        log_change(cfg, "C:\\music\\a.mp3", 0)
        self.assertFalse(os.path.exists(self.chg))

    # --- check_writable ---

    def test_check_writable_ok(self):
        target = os.path.join(self.tmp, "new.log")
        self.assertTrue(check_writable(target))  # 없으면 생성 가능해야 True

    def test_check_writable_empty_false(self):
        self.assertFalse(check_writable(""))

    def test_check_writable_bad_dir_false(self):
        bad = os.path.join(self.tmp, "no_such_dir", "x.log")
        self.assertFalse(check_writable(bad))


if __name__ == "__main__":
    unittest.main()
