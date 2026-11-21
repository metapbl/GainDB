# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""시작 언어 결정(D083·D090)과 Language 메뉴 표기(D084). 사용자 QSettings 는 건드리지 않는다."""

from __future__ import annotations

import os
import re
import unittest
from unittest import mock

ALL = ("en", "ko", "zh_CN", "ja", "es", "ru")


class ResolveLanguageTest(unittest.TestCase):
    def setUp(self) -> None:
        from PySide6.QtCore import QSettings
        import gui.i18n as i18n
        self.i18n = i18n
        for p in (mock.patch.object(i18n, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(i18n, "_SETTINGS_APP", "GaindBTest"),
                  # 규칙은 번역 파일과 별개로 6개 언어 기준으로 본다.
                  mock.patch.object(i18n, "SUPPORTED", ALL)):
            p.start()
            self.addCleanup(p.stop)
        self.settings = QSettings("GaindBTest", "GaindBTest")
        self.settings.clear()
        self.addCleanup(self.settings.clear)

    def resolve(self, locale: str) -> str:
        from PySide6.QtCore import QLocale
        with mock.patch.object(self.i18n.QLocale, "system", return_value=QLocale(locale)):
            return self.i18n.resolve_language()

    def test_locale_without_saved_value(self):
        cases = {"ko_KR": "ko", "ja_JP": "ja", "zh_CN": "zh_CN", "zh_SG": "zh_CN",
                 "zh_TW": "en", "zh_HK": "en", "es_ES": "es", "es_MX": "es",
                 "ru_RU": "ru", "fr_FR": "en", "en_US": "en"}
        for loc, want in cases.items():
            with self.subTest(locale=loc):
                self.assertEqual(self.resolve(loc), want)

    def test_saved_choice_wins_over_locale(self):
        self.settings.setValue("i18n/language", "ko")
        self.assertEqual(self.resolve("ja_JP"), "ko")

    def test_unsupported_saved_value_falls_back_to_locale(self):
        self.settings.setValue("i18n/language", "xx")
        self.assertEqual(self.resolve("ru_RU"), "ru")


class LanguageMenuTest(unittest.TestCase):
    def test_menu_lists_native_names_in_every_language(self):
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.main_window as mw
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
                acts = win.menu_language.actions()
                self.assertEqual([a.text() for a in acts], list(LANGUAGES.values()))
                self.assertEqual([a.data() for a in acts if a.isChecked()], [lang])
                win.deleteLater()


class LayoutPerLanguageTest(unittest.TestCase):
    def test_default_size_has_no_horizontal_scroll_in_every_language(self):
        """D086: 번역된 머리글로 폭을 잡아도 첫 창에 가로 스크롤이 없다(D069)."""
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.main_window as mw
        from gui.i18n import LANGUAGES, install_translator
        app = QApplication.instance() or QApplication([])
        self.addCleanup(install_translator, app, "en")
        self.addCleanup(lambda: QSettings("GaindBTest", "GaindBTest").clear())
        for lang in LANGUAGES:
            with self.subTest(lang=lang), \
                    mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"), \
                    mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest"), \
                    mock.patch.object(mw, "resolve_language", return_value=lang):
                self.assertEqual(install_translator(app, lang), lang)
                win = mw.MainWindow()
                win.model.add_paths(["a.mp3", "b.mp3"])
                win.resize(*win._default_window_extent())
                win.show()
                app.processEvents()
                self.assertEqual(win.table.horizontalScrollBar().maximum(), 0)
                win.hide()
                win.deleteLater()


if __name__ == "__main__":
    unittest.main()


class LanguageBehaviourTest(unittest.TestCase):
    """F9 인수 기준 1·3·7. 사용자 QSettings 대신 GaindBTest 를 쓴다."""

    def setUp(self) -> None:
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtCore import QSettings
        from PySide6.QtWidgets import QApplication
        import gui.i18n as i18n
        import gui.main_window as mw
        self.mw, self.i18n = mw, i18n
        self.app = QApplication.instance() or QApplication([])
        for p in (mock.patch.object(mw, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(mw, "_SETTINGS_APP", "GaindBTest"),
                  mock.patch.object(i18n, "_SETTINGS_ORG", "GaindBTest"),
                  mock.patch.object(i18n, "_SETTINGS_APP", "GaindBTest")):
            p.start()
            self.addCleanup(p.stop)
        self.addCleanup(i18n.install_translator, self.app, "en")
        QSettings("GaindBTest", "GaindBTest").clear()
        self.addCleanup(lambda: QSettings("GaindBTest", "GaindBTest").clear())

    def window(self, lang: str):
        self.i18n.install_translator(self.app, lang)
        with mock.patch.object(self.mw, "resolve_language", return_value=lang):
            win = self.mw.MainWindow()
        self.addCleanup(win.deleteLater)
        return win

    def test_ja_standard_buttons_are_japanese(self):
        from PySide6.QtWidgets import QDialogButtonBox
        self.i18n.install_translator(self.app, "ja")
        box = QDialogButtonBox(QDialogButtonBox.StandardButton.Cancel)
        self.addCleanup(box.deleteLater)
        self.assertIn("キャンセル", box.button(QDialogButtonBox.StandardButton.Cancel).text())

    def test_switch_to_russian_now_and_after_restart(self):
        win = self.window("en")
        ru = next(a for a in win.menu_language.actions() if a.data() == "ru")
        ru.trigger()
        self.assertEqual(win.menu_analysis.title(), "Анализ")
        self.assertEqual([a.text() for a in win.menu_language.actions()],
                         list(self.i18n.LANGUAGES.values()))
        from PySide6.QtCore import QLocale
        with mock.patch.object(self.i18n.QLocale, "system", return_value=QLocale("en_US")):
            self.assertEqual(self.i18n.resolve_language(), "ru")

    def test_russian_summaries_have_no_english(self):
        # 보존 용어(D091)와 숫자를 빼고 라틴 문자 낱말이 남으면 번역 안 된 조각이다.
        win = self.window("ru")
        bar = win.statusBar()
        win._analyzed_count, win._applied_count, win._failed_count = 2, 3, 1
        win._action_done = 2
        win._on_worker_finished()
        msgs = [bar.currentMessage()]
        win._on_apply_finished()
        msgs.append(bar.currentMessage())
        for verb in (win.tr("Undoing"), "other"):
            win._action_verb = verb
            win._on_file_action_finished()
            msgs.append(bar.currentMessage())
        win._show_summary(["x"], cancelled=True)
        msgs.append(bar.currentMessage().replace("x", ""))
        for msg in msgs:
            with self.subTest(msg=msg):
                self.assertTrue(msg)
                self.assertEqual(re.findall(r"[A-Za-z]{2,}", msg), [])
