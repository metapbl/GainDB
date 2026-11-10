# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""원본 mp3gain GUI 옵션 테스트 (F8, D071~D073). 파일 작업은 tempfile 사본에서만."""

from __future__ import annotations

import os
from unittest import mock

from tests._support import BaseGainTest
from tests.test_gui_window import WindowTestBase

OLD = 1577836800  # 2020-01-01 00:00:00 UTC


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


class PreserveTimeWorkerTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        _qt_app()

    def _old_copy(self, name="test_gain_44k.mp3"):
        path = self.copy_fixture(name)
        os.utime(path, (OLD, OLD))
        return path

    def _mtime(self, path):
        return int(os.stat(path).st_mtime)

    def test_track_gain_undo_and_remove_tags_keep_time(self):
        from gaindb.api import DEFAULT_TARGET_DB
        from gui.workers import ApplyWorker, FileActionWorker
        path = self._old_copy()
        before = self.audio_body_sha256(path)

        ApplyWorker([path], DEFAULT_TARGET_DB, {}, save_timestamp=True).run()
        self.assertNotEqual(self.audio_body_sha256(path), before)
        self.assertEqual(self._mtime(path), OLD)

        FileActionWorker([path], "undo", save_timestamp=True).run()
        self.assertEqual(self.audio_body_sha256(path), before)
        self.assertEqual(self._mtime(path), OLD)

        FileActionWorker([path], "remove_tags", save_timestamp=True).run()
        self.assertEqual(self._mtime(path), OLD)

    def test_album_gain_keeps_time(self):
        from gaindb.api import DEFAULT_TARGET_DB, group_by_album
        from gui.workers import AlbumApplyWorker
        paths = [self._old_copy("test_gain_44k.mp3"), self._old_copy("test_gain_48k.mp3")]
        before = self.audio_body_sha256(paths[0])
        AlbumApplyWorker(group_by_album(paths, each_folder_is_album=False),
                         DEFAULT_TARGET_DB, {}, save_timestamp=True).run()
        self.assertNotEqual(self.audio_body_sha256(paths[0]), before)
        self.assertEqual([self._mtime(p) for p in paths], [OLD, OLD])

    def test_off_changes_time(self):
        from gaindb.api import DEFAULT_TARGET_DB
        from gui.workers import ApplyWorker
        path = self._old_copy()
        ApplyWorker([path], DEFAULT_TARGET_DB, {}).run()
        self.assertNotEqual(self._mtime(path), OLD)


class TrackNoClipTest(BaseGainTest):
    """Don't clip when doing Track Gain: 원본 GUI 식 (D072)."""

    def test_rule(self):
        from gaindb.apply_gain import track_no_clip_steps
        # 최대 스텝 = floor(4·log2(32767 / (peak·32768)))
        self.assertEqual(track_no_clip_steps(10, 0.5), 3)
        self.assertEqual(track_no_clip_steps(2, 0.5), 2)      # 제안이 더 작으면 그대로
        self.assertEqual(track_no_clip_steps(0, 1.2), -2)     # 제안 0 이어도 낮춘다
        self.assertEqual(track_no_clip_steps(5, 0.0), 0)      # 진폭 0 이면 최대 스텝 0(원본)

    def _apply(self, no_clip):
        from gaindb.api import analyze_file, apply_file_track_gain
        path = self.copy_fixture("test_gain_44k.mp3")
        seed = analyze_file(path, 105.0)  # 높은 목표로 클리핑을 만든다
        res = apply_file_track_gain(path, 105.0, seed=seed, track_no_clip=no_clip)
        return seed, res

    def test_lowers_to_max_no_clip(self):
        from math import floor, log2
        seed, res = self._apply(True)
        want = floor(4 * log2(32767 / (seed["peak"] * 32768)))
        self.assertLess(want, seed["steps"])
        self.assertEqual(res["steps"], want)

    def test_off_applies_suggested(self):
        seed, res = self._apply(False)
        self.assertEqual(res["steps"], seed["steps"])


class OptionMenuTest(WindowTestBase):
    def test_preserve_time_persists_and_reaches_workers(self):
        self.assertFalse(self.win.act_preserve_time.isChecked())
        self.win.act_preserve_time.setChecked(True)
        again = self.mw.MainWindow()
        self.addCleanup(again.deleteLater)
        self.assertTrue(again.act_preserve_time.isChecked())
        self.assertEqual(again.act_preserve_time.text(), "Preserve file date/time")

        self.win.table.selectRow(0)
        self.addCleanup(setattr, self.win, "_worker", None)
        with mock.patch.object(self.mw, "ApplyWorker") as worker:
            self.win._on_gain()
        self.assertTrue(worker.call_args.kwargs["save_timestamp"])

    def test_track_no_clip_persists_and_reaches_worker(self):
        self.assertFalse(self.win.act_track_no_clip.isChecked())
        self.win.act_track_no_clip.setChecked(True)
        again = self.mw.MainWindow()
        self.addCleanup(again.deleteLater)
        self.assertTrue(again.act_track_no_clip.isChecked())

        self.win.table.selectRow(0)
        self.addCleanup(setattr, self.win, "_worker", None)
        with mock.patch.object(self.mw, "ApplyWorker") as worker:
            self.win._on_gain()
        self.assertTrue(worker.call_args.kwargs["track_no_clip"])
