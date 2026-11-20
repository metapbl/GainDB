# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""시작 언어 결정(D083·D090)과 Language 메뉴 표기(D084). 사용자 QSettings 는 건드리지 않는다."""

from __future__ import annotations

import os
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


if __name__ == "__main__":
    unittest.main()
