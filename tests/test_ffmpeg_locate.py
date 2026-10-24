# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""F6 ffmpeg 찾기 테스트.

PATH 와 OS별 후보 폴더(gaindb.decode._CANDIDATE_DIRS)를 임시 폴더로 바꿔
ffmpeg/ffprobe 의 위치를 흉내 낸다. 가짜 실행 파일은 빈 파일이며 실행하지
않는다(찾기 결과만 확인). fixture 는 BaseGainTest 의 tempfile 사본에서만 다룬다.
"""

from __future__ import annotations

import io
import os
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

import gaindb_cli
from gaindb.decode import DecodeError, decode_pcm, find_ffmpeg
from tests._support import BaseGainTest, _sha256

_EXE = ".exe" if sys.platform == "win32" else ""


def _patch_locations(test: unittest.TestCase, path: str, candidates) -> None:
    """PATH 와 후보 폴더를 테스트 동안만 바꾼다."""
    for p in (mock.patch.dict(os.environ, {"PATH": path}),
              mock.patch("gaindb.decode._CANDIDATE_DIRS", tuple(candidates))):
        p.start()
        test.addCleanup(p.stop)


class FindFfmpegTest(unittest.TestCase):
    def setUp(self) -> None:
        tmp = tempfile.TemporaryDirectory(prefix="gaindb_locate_")
        self.addCleanup(tmp.cleanup)
        self._root = Path(tmp.name)

    def _dir(self, name: str, *tools: str) -> str:
        d = self._root / name
        d.mkdir()
        for t in tools:
            f = d / (t + _EXE)
            f.touch()
            f.chmod(0o755)
        return str(d)

    def _expect(self, found, folder: str) -> None:
        want = (os.path.join(folder, "ffmpeg" + _EXE),
                os.path.join(folder, "ffprobe" + _EXE))
        self.assertEqual([os.path.normcase(p) for p in found],
                         [os.path.normcase(p) for p in want])

    def test_path_wins_over_candidates(self):
        on_path = self._dir("path", "ffmpeg", "ffprobe")
        cand = self._dir("cand", "ffmpeg", "ffprobe")
        _patch_locations(self, on_path, [cand])
        self._expect(find_ffmpeg(), on_path)

    def test_second_candidate_when_path_and_first_empty(self):
        on_path = self._dir("path")
        first = self._dir("cand1")
        second = self._dir("cand2", "ffmpeg", "ffprobe")
        _patch_locations(self, on_path, [first, second])
        self._expect(find_ffmpeg(), second)

    def test_does_not_mix_sources(self):
        on_path = self._dir("path", "ffmpeg")
        first = self._dir("cand1", "ffmpeg", "ffprobe")
        _patch_locations(self, on_path, [first])
        self._expect(find_ffmpeg(), first)

    def test_nowhere_lists_every_location(self):
        on_path = self._dir("path")
        first = self._dir("cand1", "ffprobe")
        second = self._dir("cand2")
        _patch_locations(self, on_path, [first, second])
        with self.assertRaises(DecodeError) as cm:
            find_ffmpeg()
        msg = str(cm.exception)
        for loc in ("PATH", first, second):
            self.assertIn(loc, msg)


class NoFfmpegTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        empty = tempfile.mkdtemp(prefix="gaindb_nopath_", dir=self._tmpdir)
        _patch_locations(self, empty, [])

    def test_decode_raises_and_leaves_file_unchanged(self):
        copy = self.copy_fixture("test_gain_44k.mp3")
        before = _sha256(Path(copy))
        with self.assertRaises(DecodeError):
            decode_pcm(Path(copy))
        self.assertEqual(_sha256(Path(copy)), before)

    def _run_inproc(self, args):
        # PATH 패치가 subprocess 에는 의미가 달라지므로 CLI 를 in-process 로 돌린다.
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            rc = gaindb_cli.main(["gaindb_cli.py", *args])
        return rc, out.getvalue() + err.getvalue()

    def test_cli_analysis_reports_each_file_and_exits_1(self):
        files = [self.copy_fixture("test_gain_44k.mp3"),
                 self.copy_fixture("test_gain_48k.mp3")]
        before = [_sha256(Path(f)) for f in files]
        rc, output = self._run_inproc(files)
        self.assertEqual(rc, 1)
        self.assertEqual(output.count("ffmpeg/ffprobe not found"), 2, output)
        self.assertIn("Searched: PATH", output)
        self.assertEqual([_sha256(Path(f)) for f in files], before)

    def test_cli_check_tags_needs_no_ffmpeg(self):
        f = self.copy_fixture("test_gain_44k.mp3")
        rc, output = self._run_inproc(["-s", "c", f])
        self.assertEqual(rc, 0, output)
        self.assertNotIn("not found", output)
