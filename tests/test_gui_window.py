# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""메인 창 동작 테스트(offscreen). 파일은 경로 문자열만 쓰고 건드리지 않는다."""

from __future__ import annotations

import os
import unittest
from unittest import mock


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


class ClipColorTest(WindowTestBase):
    def test_clip_colors(self):
        from PySide6.QtCore import Qt
        from PySide6.QtGui import QColor
        from gui.columns import Col
        row = self.win.model.get_row(0)
        index = self.win.model.index(0, int(Col.CLIP))
        role = Qt.ItemDataRole.ForegroundRole
        row.result = {"clip_state": "possible"}
        self.assertEqual(self.win.model.data(index, role), QColor(0, 0, 255))
        row.result = {"clip_state": "definite"}
        self.assertEqual(self.win.model.data(index, role), QColor(255, 0, 0))
        row.result = {"clip_state": "none"}
        self.assertIsNone(self.win.model.data(index, role))


class DeleteKeyTest(WindowTestBase):
    def test_delete_removes_selected_row(self):
        from PySide6.QtCore import Qt
        self.win.table.selectRow(0)
        self.press(Qt.Key.Key_Delete)
        self.assertEqual(self.win.model.rowCount(), 1)

    def test_backspace_keeps_rows(self):
        from PySide6.QtCore import Qt
        self.win.table.selectRow(0)
        self.press(Qt.Key.Key_Backspace)
        self.assertEqual(self.win.model.rowCount(), 2)


class MenuStateTest(WindowTestBase):
    def test_selection_actions_enabled_without_selection(self):
        self.win.table.clearSelection()
        self.win._update_action_states()
        self.assertTrue(self.win.act_clear_analysis.isEnabled())
        self.assertTrue(self.win.act_undo.isEnabled())


class CloseEventTest(WindowTestBase):
    def test_close_terminates_stuck_worker(self):
        for kind in ("scan", "analyze", "apply", "action", "album_apply"):
            with self.subTest(kind=kind):
                worker = self.close_while_running(kind)
                worker.request_cancel.assert_called_once()
                worker.terminate.assert_called_once()


class RemoveTagsTest(WindowTestBase):
    def test_remove_tags_starts_without_asking(self):
        self.win.table.selectRow(0)
        with mock.patch.object(self.mw, "FileActionWorker") as worker, \
                mock.patch.object(self.mw.QMessageBox, "question") as ask:
            self.addCleanup(setattr, self.win, "_worker", None)
            self.win._on_ctx_remove_tags()
        ask.assert_not_called()
        self.assertEqual(worker.call_args.args[1], "remove_tags")


if __name__ == "__main__":
    unittest.main()
