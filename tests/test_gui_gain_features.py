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


class CoreEntryPointTest(BaseGainTest):
    """F10 코어 진입점: CLI -g / -l / -x 와 같은 결과 (D102, D103)."""

    def _pair(self, name):
        import shutil
        a = self.copy_fixture(name)
        b = a[:-4] + "_cli.mp3"
        shutil.copy2(a, b)
        return a, b

    def test_constant_gain_matches_cli_g(self):
        from gaindb.api import apply_file_constant_gain
        a, b = self._pair("test_gain_44k.mp3")
        before = self.audio_body_sha256(a)
        apply_file_constant_gain(a, 3)
        r = self.run_cli(["-g", "3", b])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertNotEqual(self.audio_body_sha256(a), before)
        self.assertEqual(_bytes(a), _bytes(b))

    def test_one_channel_matches_cli_l(self):
        from gaindb.api import apply_file_constant_gain
        a, b = self._pair("test_stereo_44k.mp3")
        apply_file_constant_gain(a, -2, channel=1)
        r = self.run_cli(["-l", "1", "-2", b])
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(_bytes(a), _bytes(b))

    def _tag_table(self, *paths):
        from tests.test_mp3gain_parity import _table
        r = self.run_cli(["-s", "c", "-o", *paths])
        self.assertEqual(r.returncode, 0, r.stderr)
        return _table(r.stdout)

    def test_max_amp_matches_cli_x_and_writes_amp_tags(self):
        # 원본 GUI Max No-clip analysis 는 한 곡씩 mp3gain /x: 진폭·min/max 만 태그에 (D108)
        from math import floor, log2
        from gaindb.api import analyze_file_max_amp
        path, cli = self._pair("test_gain_44k.mp3")
        res = analyze_file_max_amp(path)

        r = self.run_cli(["-x", "-o", cli])
        self.assertEqual(r.returncode, 0, r.stderr)
        cols = [l.split("	") for l in r.stdout.splitlines() if l.startswith(cli)][0]
        self.assertAlmostEqual(res["peak"] * 32768.0, float(cols[3]), places=3)
        self.assertEqual((res["max_gain"], res["min_gain"]), (int(cols[4]), int(cols[5])))
        self.assertEqual(res["max_noclip_steps"],
                         floor(4 * log2(32767 / (res["peak"] * 32768))))

        got = self._tag_table(path)["test_gain_44k.mp3"]
        self.assertEqual(got[:2], ["NA", "NA"])                 # Track gain 없음
        self.assertAlmostEqual(float(got[2]), res["peak"] * 32768.0, delta=0.1)  # 태그는 소수 6자리
        self.assertEqual(got[3:5], [str(res["max_gain"]), str(res["min_gain"])])
        self.assertEqual(got, self._tag_table(cli)["test_gain_44k_cli.mp3"])

    def test_cli_x_album_writes_amp_not_gain(self):
        # mp3gain -x 여러 파일: Album 진폭·min/max 만, Album gain 은 쓰지 않는다 (D108, CI 원본 대조)
        a, b = self._pair("test_gain_44k.mp3")
        r = self.run_cli(["-x", a, b])
        self.assertEqual(r.returncode, 0, r.stderr)
        for row in self._tag_table(a, b).values():
            self.assertEqual([row[0], row[1], row[5], row[6]], ["NA"] * 4)
            self.assertNotIn("NA", row[2:5] + row[7:10])


class ConstantGainDialogTest(BaseGainTest):
    """원본 frmGetGain: 슬라이더 -8~+8, dB 표시, 한 채널 옵션 (D103)."""

    def setUp(self) -> None:
        super().setUp()
        _qt_app()
        from gui.dialogs.constant_gain_dialog import ConstantGainDialog
        self.dlg = ConstantGainDialog()
        self.addCleanup(self.dlg.deleteLater)

    def test_slider_and_db_label(self):
        self.assertEqual((self.dlg.slider.minimum(), self.dlg.slider.maximum()), (-8, 8))
        self.assertEqual(self.dlg.steps(), 0)
        self.dlg.slider.setValue(3)
        self.assertEqual(self.dlg.steps(), 3)
        self.assertEqual(self.dlg.lbl_db.text(), "4.5")
        self.dlg.slider.setValue(-8)
        self.assertEqual(self.dlg.lbl_db.text(), "-12.0")

    def test_one_channel(self):
        self.assertIsNone(self.dlg.channel())
        self.assertFalse(self.dlg.rb_left.isEnabled())
        self.dlg.chk_one.setChecked(True)
        self.assertTrue(self.dlg.rb_left.isEnabled())
        self.assertEqual(self.dlg.channel(), 0)          # 기본 왼쪽
        self.dlg.rb_right.setChecked(True)
        self.assertEqual(self.dlg.channel(), 1)


class ConstantGainWindowTest(WindowTestBase):
    def _run(self, steps, channel=None, accepted=True):
        from unittest import mock
        from PySide6.QtWidgets import QDialog
        dlg = mock.MagicMock()
        dlg.exec.return_value = (QDialog.DialogCode.Accepted if accepted
                                 else QDialog.DialogCode.Rejected)
        dlg.steps.return_value = steps
        dlg.channel.return_value = channel
        self.addCleanup(setattr, self.win, "_worker", None)
        with mock.patch.object(self.mw, "ConstantGainDialog", return_value=dlg), \
                mock.patch.object(self.mw, "FileActionWorker") as worker:
            self.win.act_constant_gain.trigger()
        return worker

    def test_menu_item(self):
        act = self.win.act_constant_gain
        self.assertEqual(act.text(), "Apply Constant Gain...")
        self.assertEqual(act.shortcut().toString(), "Ctrl+O")
        acts = self.win.menu_modify.actions()
        self.assertIs(acts[acts.index(self.win.act_album_gain) + 1], act)
        self.assertNotIn(act, self.win.ctx_menu.actions())

    def test_applies_to_all_rows_without_selection(self):
        worker = self._run(3, 1)
        self.assertEqual(worker.call_args.args[:2], (["a.mp3", "b.mp3"], "constant"))
        self.assertEqual((worker.call_args.kwargs["steps"],
                          worker.call_args.kwargs["channel"]), (3, 1))

    def test_zero_or_cancel_does_nothing(self):
        self._run(0).assert_not_called()
        self._run(3, accepted=False).assert_not_called()


class ConstantGainWorkerTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        _qt_app()

    def test_matches_cli_and_undo_restores(self):
        import shutil
        from gui.workers import FileActionWorker
        a = self.copy_fixture("test_gain_44k.mp3")
        s = self.copy_fixture("test_stereo_44k.mp3")
        cli = [shutil.copy2(p, p[:-4] + "_cli.mp3") for p in (a, s)]
        before = self.audio_body_sha256(a)
        changed = []
        w = FileActionWorker([a], "constant", steps=3)
        w.row_gain_changed.connect(lambda p, n: changed.append(n))
        w.run()
        FileActionWorker([s], "constant", steps=-2, channel=1).run()
        self.assertEqual(self.run_cli(["-g", "3", cli[0]]).returncode, 0)
        self.assertEqual(self.run_cli(["-l", "1", "-2", cli[1]]).returncode, 0)
        self.assertEqual(changed, [3])
        self.assertEqual(_bytes(a), _bytes(cli[0]))
        self.assertEqual(_bytes(s), _bytes(cli[1]))

        FileActionWorker([a], "undo").run()
        self.assertEqual(self.audio_body_sha256(a), before)
