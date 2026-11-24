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


class HeaderFitTest(unittest.TestCase):
    """F11 인수 기준 1: 언어를 바꾸거나 다시 실행해도 머리글이 잘리지 않는다 (D111)."""

    def setUp(self) -> None:
        import os
        from unittest import mock
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.main_window as mw
        from gui.i18n import install_translator
        self.app = QApplication.instance() or QApplication([])
        self.mw = mw
        for p in (mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest")):
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
