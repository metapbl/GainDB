# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""창 폭·머리글·선택·언어 테스트 (F11, D111~D115)."""

from __future__ import annotations

import unittest


class WrapHeaderTest(unittest.TestCase):
    """머리글 두 줄 규칙(D115). 폭은 글자 수로 재서 글꼴과 무관하게 본다."""

    def wrap(self, text):
        from gui.columns import wrap_header
        return wrap_header(text, len)

    def test_splits_at_space_and_before_parenthesis(self):
        self.assertEqual(self.wrap("Track Gain"), ("Track\nGain", 5))
        self.assertEqual(self.wrap("clip(Album)"), ("clip\n(Album)", 7))
        self.assertEqual(self.wrap("클립(앨범)"), ("클립\n(앨범)", 4))
        self.assertEqual(self.wrap("앨범 볼륨"), ("앨범\n볼륨", 2))

    def test_never_inside_hangul_or_latin_word(self):
        for word in ("볼륨", "클리핑", "Volume", "clipping", "saturación"):
            with self.subTest(word=word):
                self.assertEqual(self.wrap(word), (word, len(word)))

    def test_japanese_splits_only_where_script_changes(self):
        self.assertEqual(self.wrap("トラックゲイン"), ("トラックゲイン", 7))
        self.assertEqual(self.wrap("アルバム音量"), ("アルバム\n音量", 4))
        self.assertEqual(self.wrap("現在の最大振幅"), ("現在の\n最大振幅", 4))

    def test_chinese_splits_every_two_han(self):
        self.assertEqual(self.wrap("音轨增益"), ("音轨\n增益", 2))
        self.assertEqual(self.wrap("当前最大振幅"), ("当前\n最大振幅", 4))
        self.assertEqual(self.wrap("削波"), ("削波", 2))
        self.assertEqual(self.wrap("削波(专辑)"), ("削波\n(专辑)", 4))


# 1.3.1 의 숫자 컬럼 최소 폭과 Path\File 폭 (폭 비교 기준, 같은 환경에서 다시 계산한다)
_OLD_MIN = {1: 72, 2: 80, 3: 72, 5: 100, 6: 88, 7: 88, 8: 104}
_OLD_NAME = 420


class NarrowWindowTest(unittest.TestCase):
    """F11 인수 기준 2: 첫 창이 1.3.1 보다 20% 이상 좁고, 머리글이 다 보인다 (D115)."""

    def test_six_languages(self):
        import os
        from unittest import mock
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QCoreApplication, QSettings, Qt
        from PySide6.QtWidgets import QApplication
        import gui.main_window as mw
        from gui.columns import COLUMNS, Col
        from gui.i18n import LANGUAGES, install_translator
        app = QApplication.instance() or QApplication([])
        self.addCleanup(install_translator, app, "en")
        self.addCleanup(lambda: QSettings("GaindBTest", "GaindBTest").clear())
        for lang in LANGUAGES:
            with self.subTest(lang=lang), \
                    mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"), \
                    mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest"), \
                    mock.patch.object(mw, "resolve_language", return_value=lang):
                install_translator(app, lang)
                win = mw.MainWindow()
                self.addCleanup(win.deleteLater)
                fm = win.table.horizontalHeader().fontMetrics()
                new = sum(win.table.columnWidth(i) for i in range(len(COLUMNS)))
                old = _OLD_NAME
                for i, w in _OLD_MIN.items():
                    tr = QCoreApplication.translate("FileTableModel", COLUMNS[i].header)
                    old += max(w, fm.horizontalAdvance(COLUMNS[i].header) + 30,
                               fm.horizontalAdvance(tr) + 30)
                extra = win._default_window_extent()[0] - new
                self.assertLessEqual(new + extra, 0.8 * (old + extra))
                for c in COLUMNS:
                    if c.index == Col.NAME or win.table.isColumnHidden(int(c.index)):
                        continue
                    lines = win.model.headerData(int(c.index), Qt.Orientation.Horizontal).split("\n")
                    self.assertLessEqual(len(lines), 2)
                    self.assertGreaterEqual(win.table.columnWidth(int(c.index)),
                                            max(fm.horizontalAdvance(x) for x in lines) + 30)

    def test_layout_version_resets_saved_widths_once(self):
        import gui.main_window as mw
        self.assertEqual(mw._LAYOUT_VERSION, 2)


class _WindowBase(unittest.TestCase):
    """테스트 전용 설정 이름과 언어로 주 창을 만든다."""

    def setUp(self) -> None:
        import os
        from unittest import mock
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.i18n as i18n
        import gui.main_window as mw
        from gui.i18n import install_translator
        self.app = QApplication.instance() or QApplication([])
        self.mw = mw
        for p in (mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest"),
                  mock.patch.object(i18n, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(i18n, "_SETTINGS_APP", "GaindBTest")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(lambda: QSettings("GaindBTest", "GaindBTest").clear())
        self.addCleanup(install_translator, self.app, "en")
        install_translator(self.app, "en")

    def _window(self, lang):
        from unittest import mock
        with mock.patch.object(self.mw, "resolve_language", return_value=lang):
            win = self.mw.MainWindow()
        self.addCleanup(win.deleteLater)
        return win


class HeaderFitTest(_WindowBase):
    """F11 인수 기준 1: 언어를 바꾸거나 다시 실행해도 머리글이 잘리지 않는다 (D111)."""

    def _squeeze(self, win):
        # en 폭보다 좁게 저장해 둔 상황(1.3 이전 저장값·사용자가 줄인 폭). 한 컬럼은 넓혀 둔다.
        from gui.columns import Col
        for c in (Col.VOLUME, Col.TRACK_GAIN, Col.ALBUM_VOLUME, Col.MAX_AMP):
            win.table.setColumnWidth(int(c), 40)
        win.table.setColumnWidth(int(Col.CLIP), 300)

    def _assert_fit(self, win):
        from PySide6.QtCore import Qt
        from gui.columns import COLUMNS, Col
        fm = win.table.horizontalHeader().fontMetrics()
        for c in COLUMNS:
            if c.index == Col.NAME or win.table.isColumnHidden(int(c.index)):
                continue
            lines = win.model.headerData(int(c.index), Qt.Orientation.Horizontal).split("\n")
            with self.subTest(column=c.header):
                self.assertGreaterEqual(win.table.columnWidth(int(c.index)),
                                        max(map(fm.horizontalAdvance, lines)) + 30)
        self.assertEqual(win.table.columnWidth(int(Col.CLIP)), 300)   # 넓힌 폭은 그대로

    def test_language_switch(self):
        from gui.i18n import install_translator
        win = self._window("en")
        self._squeeze(win)
        install_translator(self.app, "ru")
        self.app.processEvents()
        self._assert_fit(win)

    def test_restart_with_saved_widths(self):
        from gui.i18n import install_translator
        win = self._window("en")
        self._squeeze(win)
        win._save_settings()
        install_translator(self.app, "ru")
        self._assert_fit(self._window("ru"))


class MaximizingWidensWindowTest(_WindowBase):
    """F11 인수 기준 3: 실행 중 Maximizing 을 켜면 창이 컬럼만큼 넓어진다 (D115)."""

    def _turn_on(self, win, screen_width=5000, maximized=False):
        from unittest import mock
        screen = mock.MagicMock()
        screen.availableGeometry.return_value.width.return_value = screen_width
        with mock.patch.object(self.mw.QMessageBox, "information"), \
                mock.patch.object(win, "screen", return_value=screen), \
                mock.patch.object(win, "isMaximized", return_value=maximized):
            win.act_maximizing.setChecked(True)
        self.app.processEvents()

    def test_widens_without_horizontal_scroll(self):
        win = self._window("es")
        win.model.add_paths(["a.mp3"])
        win.resize(*win._default_window_extent())
        win.show()
        self.app.processEvents()
        self._turn_on(win)
        self.assertEqual(win.width(), win._default_window_extent()[0])
        self.assertEqual(win.table.horizontalScrollBar().maximum(), 0)

    def test_capped_by_screen_and_kept_when_maximized(self):
        win = self._window("es")
        win.resize(*win._default_window_extent())
        before = win.width()
        self._turn_on(win, screen_width=before + 10)
        self.assertEqual(win.width(), before + 10)
        again = self._window("es")
        again.resize(*again._default_window_extent())
        width = again.width()
        self._turn_on(again, maximized=True)
        self.assertEqual(again.width(), width)


class SelectionMenuTest(_WindowBase):
    """F11 인수 기준 4: 원본 파일 메뉴의 선택 항목 3개 (D113)."""

    def test_select_all_none_invert(self):
        win = self._window("en")
        win.model.add_paths(["a.mp3", "b.mp3", "c.mp3"])
        count = lambda: len(win.table.selectionModel().selectedRows())
        win.act_select_all.trigger()
        self.assertEqual(count(), 3)
        win.act_select_none.trigger()
        self.assertEqual(count(), 0)
        win.table.selectRow(1)
        win.act_invert_selection.trigger()
        self.assertEqual(count(), 2)
        self.assertNotIn(1, [i.row() for i in win.table.selectionModel().selectedRows()])

    def test_menu_place_and_shortcuts(self):
        from PySide6.QtGui import QAction
        win = self._window("en")
        acts = win.menu_file.actions()
        i = acts.index(win.act_add_folder)
        self.assertTrue(acts[i + 1].isSeparator())
        self.assertEqual(acts[i + 2:i + 5],
                         [win.act_select_all, win.act_select_none, win.act_invert_selection])
        self.assertTrue(acts[i + 5].isSeparator())
        self.assertEqual([(a.text(), a.shortcut().toString()) for a in acts[i + 2:i + 5]],
                         [("Select All Files", "Ctrl+A"), ("Select No Files", "Ctrl+N"),
                          ("Invert selection", "Ctrl+V")])
        keys = [a.shortcut().toString() for a in win.findChildren(QAction) if not a.shortcut().isEmpty()]
        self.assertEqual(len(keys), len(set(keys)))


class SelectionWhileBusyTest(_WindowBase):
    """D117: 원본처럼 작업 중에는 선택 메뉴를 끄고, 시작 포커스는 파일 표."""

    def test_disabled_while_busy(self):
        from unittest import mock
        win = self._window("en")
        acts = (win.act_select_all, win.act_select_none, win.act_invert_selection)
        self.assertTrue(all(a.isEnabled() for a in acts))
        with mock.patch.object(win, "_is_busy", return_value=True):
            win._update_action_states()
            self.assertFalse(any(a.isEnabled() for a in acts))
        win._update_action_states()
        self.assertTrue(all(a.isEnabled() for a in acts))

    def test_start_focus_on_table(self):
        win = self._window("en")
        self.assertIs(win.focusWidget(), win.table)


class LanguageSwitchWidensWindowTest(_WindowBase):
    """D117: 언어를 바꿔 컬럼이 넓어지면 Maximizing 때와 같은 규칙으로 창도 넓힌다."""

    def test_en_to_ru_no_horizontal_scroll(self):
        from unittest import mock
        from gui.i18n import install_translator
        win = self._window("en")
        from gui.columns import Col
        win.model.add_paths(["a.mp3"])
        # 새 언어 머리글이 더 넓은 상황: 테스트 환경 글꼴은 언어마다 폭이 같아 컬럼을 미리 좁혀 둔다
        win.table.setColumnWidth(int(Col.ALBUM_VOLUME), 20)
        win.resize(*win._default_window_extent())
        win.show()
        self.app.processEvents()
        screen = mock.MagicMock()
        screen.availableGeometry.return_value.width.return_value = 5000
        with mock.patch.object(win, "screen", return_value=screen):
            install_translator(self.app, "ru")
            self.app.processEvents()
        self.assertEqual(win.width(), win._default_window_extent()[0])
        self.assertEqual(win.table.horizontalScrollBar().maximum(), 0)

    def test_no_widen_when_no_column_grew(self):
        # 넓어진 컬럼이 없으면 사용자가 줄여 둔 창을 그대로 둔다
        from gui.columns import COLUMNS, Col
        from gui.i18n import install_translator
        win = self._window("en")
        # 어느 플랫폼 글꼴에서도 러시아어 머리글보다 넓게 둬서 넓어질 컬럼이 없게 한다
        for c in COLUMNS:
            if c.index != Col.NAME:
                win.table.setColumnWidth(int(c.index), 400)
        width, height = win._default_window_extent()
        win.resize(width - 100, height)
        win.show()
        self.app.processEvents()  # 최소 폭·화면 폭은 이벤트 처리 뒤 적용된다
        narrowed = win.width()
        self.assertLess(narrowed, width)
        install_translator(self.app, "ru")
        self.app.processEvents()
        self.assertEqual(win.width(), narrowed)
