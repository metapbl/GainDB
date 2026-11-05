# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""메인 창 동작 테스트(offscreen). 파일은 경로 문자열만 쓰고 건드리지 않는다."""

from __future__ import annotations

import ast
import os
import shutil
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
