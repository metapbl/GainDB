# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""메인 창 동작 테스트(offscreen). 파일은 경로 문자열만 쓰고 건드리지 않는다."""

from __future__ import annotations

import ast
import os
import shutil
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest import mock

from tests._support import BaseGainTest
from tests.test_mp3gain_parity import _table


class WindowTestBase(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.main_window as mw
        self.app = QApplication.instance() or QApplication([])
        self.mw = mw
        for p in (mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest"),
                  mock.patch.object(mw, "resolve_language", return_value="en")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: QSettings("GaindBTest", "GaindBTest").clear())
        self.win = mw.MainWindow()
        self.addCleanup(self.win.deleteLater)
        self.win.model.add_paths(["a.mp3", "b.mp3"])

    def press(self, key) -> None:
        from PySide6.QtCore import QEvent, Qt
        from PySide6.QtGui import QKeyEvent
        from PySide6.QtWidgets import QApplication
        QApplication.sendEvent(self.win.table, QKeyEvent(
            QEvent.Type.KeyPress, key, Qt.KeyboardModifier.NoModifier))

    def close_while_running(self, kind: str):
        from PySide6.QtGui import QCloseEvent
        worker = mock.MagicMock()
        worker.wait.return_value = False
        self.win._worker = worker
        self.win._worker_kind = kind
        self.addCleanup(setattr, self.win, "_worker", None)
        self.win.closeEvent(QCloseEvent())
        return worker


class TranslationCoverageTest(unittest.TestCase):
    """화면 문구가 ko 번역에 모두 있는지 본다. lupdate 는 f-string 안의 tr 을 못 찾는다."""

    GUI = Path(__file__).resolve().parent.parent / "gui"

    def _tr_calls(self):
        for path in self.GUI.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            in_fstring = {id(sub) for node in ast.walk(tree)
                          if isinstance(node, ast.JoinedStr) for sub in ast.walk(node)}
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                        and node.func.attr == "tr" and node.args
                        and isinstance(node.args[0], ast.Constant)):
                    yield path.name, node.args[0].value, id(node) in in_fstring

    def test_no_tr_inside_fstring(self):
        self.assertEqual([c[:2] for c in self._tr_calls() if c[2]], [])

    def test_every_tr_source_is_translated(self):
        root = ET.parse(self.GUI / "translations" / "gaindb_ko.ts").getroot()
        done = {m.findtext("source") for m in root.iter("message")
                if m.find("translation").get("type") is None
                and (m.findtext("translation") or m.find("translation").find("numerusform") is not None)}
        self.assertEqual(sorted({c[1] for c in self._tr_calls()} - done), [])


class ClipColorTest(WindowTestBase):
    def test_clip_colors_follow_theme(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from gui import theme
        from gui.columns import Col
        row = self.win.model.get_row(0)
        index = self.win.model.index(0, int(Col.CLIP))
        role = Qt.ItemDataRole.ForegroundRole
        for mode in ("dark", "light"):
            with self.subTest(mode=mode):
                theme.apply_theme(self.app, mode)
                row.result = {"clip_state": "possible"}
                self.assertEqual(self.win.model.data(index, role),
                                 QColor(theme.color("accent")))
                row.result = {"clip_state": "definite"}
                self.assertEqual(self.win.model.data(index, role),
                                 QColor(theme.color("danger")))
                row.result = {"clip_state": "none"}
                self.assertIsNone(self.win.model.data(index, role))


class FailedRowTest(WindowTestBase):
    def test_failed_row_name_is_danger_with_tooltip(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from gui import theme
        from gui.columns import Col
        self.win.model.get_row(0).mark_error("bad file")
        index = self.win.model.index(0, int(Col.NAME))
        self.assertEqual(self.win.model.data(index, Qt.ItemDataRole.ForegroundRole),
                         QColor(theme.color("danger")))
        self.assertEqual(self.win.model.data(index, Qt.ItemDataRole.ToolTipRole), "bad file")
        ok = self.win.model.index(1, int(Col.NAME))
        self.assertIsNone(self.win.model.data(ok, Qt.ItemDataRole.ForegroundRole))


class AlbumGainBrokenFileTest(BaseGainTest):
    def test_broken_file_fails_alone_and_others_apply_like_cli(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from gaindb.api import DEFAULT_TARGET_DB, group_by_album
        from gui.workers import AlbumApplyWorker
        QApplication.instance() or QApplication([])

        files = {}
        for side in ("gui", "cli"):
            d = Path(self._tmpdir) / side
            d.mkdir()
            good = [shutil.copy2(self.copy_fixture(n), d / n)
                    for n in ("test_gain_44k.mp3", "test_gain_48k.mp3")]
            broken = d / "broken.mp3"
            broken.write_bytes(b"not an mp3" * 50)
            files[side] = [str(good[0]), str(broken), str(good[1])]

        failed, applied = [], {}
        worker = AlbumApplyWorker(
            group_by_album(files["gui"], each_folder_is_album=False), DEFAULT_TARGET_DB, {})
        worker.failed.connect(lambda p, msg: failed.append(p))
        worker.row_applied.connect(lambda p, shown, steps: applied.__setitem__(p, steps))
        worker.run()
        self.assertEqual(failed, [files["gui"][1]])
        self.assertEqual(sorted(applied), sorted([files["gui"][0], files["gui"][2]]))

        r = self.run_cli(["-o", "-a", "-c", *files["cli"]])
        album_steps = int(_table(r.stdout)["Album"][0])
        self.assertEqual(set(applied.values()), {album_steps})


class LogsDialogTest(unittest.TestCase):
    def setUp(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        from gui.dialogs.logs_dialog import LogsDialog
        from gui.logging import LogConfig
        QApplication.instance() or QApplication([])
        self.config = LogConfig()
        self.dialog = LogsDialog(self.config)
        self.addCleanup(self.dialog.deleteLater)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = os.path.join(self.tmp.name, "error.log")

    def browse(self, result: str):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QFileDialog
        with mock.patch.object(QFileDialog, "getSaveFileName",
                               return_value=(result, "")) as ask:
            QTest.mouseClick(self.dialog._error.browse, Qt.MouseButton.LeftButton)
        ask.assert_called_once()

    def test_rows_are_locked_while_log_is_off(self):
        row = self.dialog._error
        self.assertFalse(row.check.isChecked())
        self.assertFalse(row.browse.isEnabled())
        self.assertFalse(row.edit.isEnabled())
        row.check.setChecked(True)
        self.assertTrue(row.browse.isEnabled())
        self.assertTrue(row.edit.isEnabled())

    def test_choosing_a_file_sets_the_path(self):
        self.dialog._error.check.setChecked(True)
        self.browse(self.path)
        self.assertEqual(self.dialog._error.path, self.path)
        self.assertTrue(self.dialog._error.enabled)

    def test_cancelling_the_file_dialog_changes_nothing(self):
        self.dialog._error.check.setChecked(True)
        self.browse("")
        self.assertEqual(self.dialog._error.path, "")

    def test_ok_does_not_create_the_file(self):
        self.dialog._error.check.setChecked(True)
        self.dialog._error.edit.setText(self.path)
        self.dialog._on_ok()
        self.assertFalse(os.path.exists(self.path))

    def test_ok_saves_a_typed_path(self):
        self.dialog._error.check.setChecked(True)
        self.dialog._error.edit.setText(self.path)
        self.dialog._on_ok()
        self.assertTrue(self.config.error_enabled)
        self.assertEqual(self.config.error_path, self.path)

    def test_turning_off_keeps_the_path(self):
        self.dialog._error.set_state(True, self.path)
        self.dialog._error.check.setChecked(False)
        self.dialog._on_ok()
        self.assertFalse(self.config.error_enabled)
        self.assertEqual(self.config.error_path, self.path)


class LogDefaultsTest(WindowTestBase):
    def test_default_paths_are_shown_but_off(self):
        c = self.win._log_config
        for kind, path, enabled in (("error", c.error_path, c.error_enabled),
                                    ("analysis", c.analysis_path, c.analysis_enabled),
                                    ("change", c.change_path, c.change_enabled)):
            with self.subTest(kind=kind):
                self.assertFalse(enabled)
                self.assertEqual(os.path.basename(path), f"GainDB-{kind}.log")
                self.assertEqual(os.path.basename(os.path.dirname(path)), "Gain dB")

    def test_analysis_logs_rows_that_already_have_values(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        log = os.path.join(tmp.name, "analysis.log")
        self.win._log_config.analysis_enabled = True
        self.win._log_config.analysis_path = log
        row = self.win.model.get_row(0)
        row.set_tag_result({"status": "ok", "track_db": -0.14, "curr_max_amp": 15530.2})
        self.win.table.selectRow(0)
        with mock.patch.object(self.mw, "AnalyzeWorker") as worker:
            self.win._on_analyze()
        worker.assert_not_called()
        with open(log, encoding="utf-8") as fh:
            line = fh.read().splitlines()[0]
        self.assertEqual(line.split("\t")[1:], ["a.mp3", "TrackdB: -0.14", "MaxAmp: 15530"])


class DefaultWindowTest(WindowTestBase):
    def test_numeric_columns_fit_their_headers(self):
        from PySide6.QtCore import Qt
        from gui.columns import COLUMNS, Col
        fm = self.win.table.horizontalHeader().fontMetrics()
        for cdef in COLUMNS:
            if cdef.index == Col.NAME:
                continue
            header = self.win.model.headerData(int(cdef.index), Qt.Orientation.Horizontal)
            with self.subTest(column=cdef.header):
                self.assertGreaterEqual(self.win.table.columnWidth(int(cdef.index)),
                                        fm.horizontalAdvance(header) + 30)

    def test_default_size_has_no_horizontal_scroll_and_golden_height(self):
        width, height = self.win._default_window_extent()
        self.assertEqual(height, round(width / 1.618))
        self.win.resize(width, height)
        self.win.show()
        self.addCleanup(self.win.hide)
        self.app.processEvents()
        self.assertEqual(self.win.table.horizontalScrollBar().maximum(), 0)

    def test_settings_from_before_1_0_are_ignored_once(self):
        from PySide6.QtCore import QSettings
        s = QSettings("GaindBTest", "GaindBTest")
        s.setValue("columns/count", 8)
        s.setValue("columns/width_1", 333)
        old = self.mw.MainWindow()
        self.addCleanup(old.deleteLater)
        self.assertNotEqual(old.table.columnWidth(1), 333)
        old._save_settings()
        s.setValue("columns/width_1", 333)
        again = self.mw.MainWindow()
        self.addCleanup(again.deleteLater)
        self.assertEqual(again.table.columnWidth(1), 333)


class DialogSmokeTest(WindowTestBase):
    """슬롯 안의 예외는 exe 에서 보이지 않으므로 대화상자 진입 경로를 직접 돌려 본다."""

    def test_dialog_handlers_run(self):
        with mock.patch.object(self.mw.AboutDialog, "exec"), \
                mock.patch.object(self.mw.LogsDialog, "exec"), \
                mock.patch.object(self.mw.QFileDialog, "getOpenFileNames",
                                  return_value=([], "")), \
                mock.patch.object(self.mw.QFileDialog, "getExistingDirectory",
                                  return_value=""):
            self.win._on_about()
            self.win._on_open_logs()
            self.win._on_add_files()
            self.win._on_add_folder()


class DeleteKeyTest(WindowTestBase):
    def test_delete_removes_selected_row(self):
        from PySide6.QtCore import Qt
        self.win.table.selectRow(0)
        self.press(Qt.Key.Key_Delete)
        self.assertEqual(self.win.model.rowCount(), 1)

    def test_backspace_removes_selected_row(self):
        from PySide6.QtCore import Qt
        self.win.table.selectRow(0)
        self.press(Qt.Key.Key_Backspace)
        self.assertEqual(self.win.model.rowCount(), 1)

    def test_shortcut_tooltip_uses_native_text(self):
        from PySide6.QtGui import QKeySequence
        native = QKeySequence("Ctrl+F").toString(QKeySequence.SequenceFormat.NativeText)
        self.assertTrue(self.win.act_add_files.toolTip().endswith(f"({native})"))


class ThemeMenuTest(WindowTestBase):
    def test_select_applies_and_persists(self):
        from PySide6.QtCore import QSettings
        from gui import theme
        self.win.act_theme_dark.trigger()
        self.assertEqual(theme.current(), "dark")
        self.win.act_theme_light.trigger()
        self.assertEqual(theme.current(), "light")
        self.assertEqual(QSettings("GaindBTest", "GaindBTest").value("ui/theme_mode"), "light")
        again = self.mw.MainWindow()
        self.addCleanup(again.deleteLater)
        self.assertTrue(again.act_theme_light.isChecked())

    def test_system_is_default(self):
        self.assertTrue(self.win.act_theme_system.isChecked())


class ProgressLabelTest(WindowTestBase):
    def test_percent_label_follows_progress(self):
        self.win.progress.setRange(0, 4000)
        self.win.progress.setValue(2000)
        self.assertEqual(self.win.lbl_percent.text(), "50%")
        self.win.progress.setValue(4000)
        self.assertEqual(self.win.lbl_percent.text(), "100%")
        self.win.progress.setValue(0)
        self.assertEqual(self.win.lbl_percent.text(), "0%")


class MenuStateTest(WindowTestBase):
    def test_selection_actions_follow_selection(self):
        self.win.table.clearSelection()
        self.assertFalse(self.win.act_clear_analysis.isEnabled())
        self.assertFalse(self.win.act_undo.isEnabled())
        self.win.table.selectRow(0)
        self.assertTrue(self.win.act_clear_analysis.isEnabled())
        self.assertTrue(self.win.act_undo.isEnabled())

    def test_selection_change_keeps_status_message(self):
        self.win.statusBar().showMessage("done")
        self.win.table.selectRow(0)
        self.assertEqual(self.win.statusBar().currentMessage(), "done")


class CloseEventTest(WindowTestBase):
    def test_close_terminates_stuck_read_only_worker(self):
        for kind in ("scan", "analyze", "album_analyze"):
            with self.subTest(kind=kind):
                worker = self.close_while_running(kind)
                worker.request_cancel.assert_called_once()
                worker.terminate.assert_called_once()

    def test_close_never_terminates_file_writing_worker(self):
        for kind in ("apply", "album_apply", "action"):
            with self.subTest(kind=kind):
                worker = self.close_while_running(kind)
                worker.request_cancel.assert_called_once()
                worker.wait.assert_called_once_with()
                worker.terminate.assert_not_called()


class RemoveTagsTest(WindowTestBase):
    def _remove_tags(self, answer):
        self.win.table.selectRow(0)
        with mock.patch.object(self.mw, "FileActionWorker") as worker, \
                mock.patch.object(self.mw.QMessageBox, "question",
                                  return_value=answer) as ask:
            self.addCleanup(setattr, self.win, "_worker", None)
            self.win._on_ctx_remove_tags()
        ask.assert_called_once()
        return worker

    def test_cancel_starts_nothing(self):
        self._remove_tags(self.mw.QMessageBox.StandardButton.No).assert_not_called()

    def test_confirm_starts_remove_tags(self):
        worker = self._remove_tags(self.mw.QMessageBox.StandardButton.Yes)
        self.assertEqual(worker.call_args.args[1], "remove_tags")


if __name__ == "__main__":
    unittest.main()
