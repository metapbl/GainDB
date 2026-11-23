# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""원본 GUI 게인 기능 테스트 (F10, D101~D107). 파일 작업은 tempfile 사본에서만."""

from __future__ import annotations

import os

from tests._support import BaseGainTest
from tests.test_gui_window import WindowTestBase

TARGET = 89.0


def _qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    from PySide6.QtWidgets import QApplication
    return QApplication.instance() or QApplication([])


def _bytes(path):
    with open(path, "rb") as f:
        return f.read()


class ZeroStepCharacterizationTest(BaseGainTest):
    """steps==0 건너뛰기(D107) 전후로 바뀌면 안 되는 Track Gain 결과."""

    def setUp(self) -> None:
        super().setUp()
        _qt_app()

    def _run(self, path, seed, target=TARGET, no_clip=False):
        from gui.workers import ApplyWorker
        applied, failed = [], []
        w = ApplyWorker([path], target, {path: seed}, track_no_clip=no_clip)
        w.row_applied.connect(lambda p, shown, steps: applied.append(steps))
        w.failed.connect(lambda p, msg: failed.append(msg))
        w.run()
        self.assertEqual(failed, [])
        return applied

    def test_analyzed_zero_step_writes_tag(self):
        # 디코딩 분석 값(태그 없음)이 0 스텝이면 코어가 태그를 기록한다.
        from gaindb.api import analyze_file, apply_file_track_gain, read_file_tags
        path = self.copy_fixture("test_gain_44k.mp3")
        apply_file_track_gain(path, TARGET, skip_tag=True)
        self.assertEqual(read_file_tags(path)["status"], "no_tag")
        audio = self.audio_body_sha256(path)
        seed = analyze_file(path, TARGET)
        self.assertEqual(seed["steps"], 0)

        self.assertEqual(self._run(path, seed), [])
        self.assertEqual(self.audio_body_sha256(path), audio)
        self.assertEqual(read_file_tags(path)["status"], "ok")

    def test_tagged_zero_step_leaves_file(self):
        from gaindb.api import apply_file_track_gain, read_file_tags
        path = self.copy_fixture("test_gain_44k.mp3")
        apply_file_track_gain(path, TARGET)
        seed = read_file_tags(path, TARGET)
        self.assertEqual(seed["steps"], 0)
        before = _bytes(path)

        self.assertEqual(self._run(path, seed), [])
        self.assertEqual(_bytes(path), before)

    def test_tagged_zero_step_lowered_by_no_clip(self):
        # 높은 목표로 적용해 클리핑 상태(최대 스텝 < 0)인 0 스텝 태그 곡을 만든다.
        from math import floor, log2
        from gaindb.api import apply_file_track_gain, read_file_tags
        path = self.copy_fixture("test_gain_44k.mp3")
        apply_file_track_gain(path, 105.0)
        seed = read_file_tags(path, 105.0)
        self.assertEqual(seed["steps"], 0)
        max_steps = floor(4 * log2(32767 / (seed["peak"] * 32768)))
        self.assertLess(max_steps, 0)

        self.assertEqual(self._run(path, seed, 105.0, no_clip=True), [max_steps])


class ZeroStepSkipTest(WindowTestBase):
    """D107: 태그 스캔 값이 0 스텝인 곡은 원본 GUI처럼 워커에 넘기지 않는다."""

    def _result(self, steps=0, peak=0.5):
        return {"status": "ok", "target_db": TARGET, "track_db": steps * 1.5,
                "steps": steps, "peak": peak}

    def _gain_paths(self):
        from unittest import mock
        self.win.table.selectAll()
        self.addCleanup(setattr, self.win, "_worker", None)
        with mock.patch.object(self.mw, "ApplyWorker") as worker, \
                mock.patch.object(self.win, "_ffmpeg_missing", return_value=False):
            self.win._on_gain()
        return worker.call_args.args[0] if worker.called else None

    def test_tag_zero_step_skipped_analyzed_kept(self):
        self.win.model.get_row(0).set_tag_result(self._result())
        self.win.model.get_row(1).set_result(self._result())
        self.assertEqual(self._gain_paths(), ["b.mp3"])

    def test_all_skipped_reports_nothing_to_apply(self):
        for r in (0, 1):
            self.win.model.get_row(r).set_tag_result(self._result())
        self.assertIsNone(self._gain_paths())
        self.assertIn("Nothing to apply", self.win.statusBar().currentMessage())

    def test_nonzero_and_applied_rows(self):
        self.win.model.get_row(0).set_tag_result(self._result(steps=2))
        self.win.model.get_row(1).mark_applied(self._result())  # 적용 뒤 태그가 있다
        self.assertEqual(self._gain_paths(), ["a.mp3"])

    def test_no_clip_lowering_not_skipped(self):
        self.win.act_track_no_clip.setChecked(True)
        self.win.model.get_row(0).set_tag_result(self._result(peak=1.2))  # 최대 스텝 < 0
        self.win.model.get_row(1).set_tag_result(self._result(peak=None))  # 진폭 모름: 낮추지 않음
        self.assertEqual(self._gain_paths(), ["a.mp3"])

    def test_other_target_uses_recomputed_steps(self):
        self.win.model.get_row(0).set_tag_result(self._result())
        self.win.model.get_row(1).set_tag_result(self._result())
        self.win.spin_target.setValue(92.0)  # 2 스텝 차이 → 둘 다 적용 대상
        self.assertEqual(self._gain_paths(), ["a.mp3", "b.mp3"])
