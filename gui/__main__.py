# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""Entry point for `python -m gui`.

Independent PySide6 front-end for the MP3 gain tool.
"""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QApplication

from gui.i18n import resolve_language, install_translator
from gui.main_window import MainWindow
from gui.resources import app_icon


def _apply_platform_font(app: QApplication) -> None:
    """Nudge the default font toward each OS's true system UI font.

    Principle: never hard-code an arbitrary font. We only *try* the font the
    OS itself intends as its default, and fall back to whatever Qt already
    picked if that font is not present. macOS / Linux are left untouched so
    their native system fonts (e.g. San Francisco) apply as-is.
    """
    if sys.platform.startswith("win"):
        # Windows 11's real UI font is "Segoe UI Variable Text". Qt otherwise
        # defaults to the legacy non-variable "Segoe UI", whose tight capital
        # kerning causes "Tr"/"Tar" glyphs to collide. The variable font's
        # optical-size axis fixes spacing at small sizes.
        candidate = QFont("Segoe UI Variable Text")
        # Keep Qt's current point size; only swap the family.
        candidate.setPointSizeF(app.font().pointSizeF())
        # Verify the family actually resolved (avoid silent substitution on
        # older Windows without the variable font).
        if QFontInfo(candidate).family().startswith("Segoe UI Variable"):
            app.setFont(candidate)
    # else: macOS / Linux -> leave the native system default alone.


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("MP3 Gain")
    # 앱 아이콘: 작업표시줄/창/트레이 공용. 파일이 없으면 빈 QIcon(무해).
    app.setWindowIcon(app_icon())
    _apply_platform_font(app)

    # 다국어: 창을 만들기 전에 언어를 결정·설치해 첫 화면부터 올바른 언어로
    # 뜨게 한다(저장값 우선, 없으면 시스템 로케일 감지 — gui/i18n 참조).
    # 이후 Language 메뉴 선택 시 install_translator 재호출로 즉시 전환된다.
    install_translator(app, resolve_language())

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())