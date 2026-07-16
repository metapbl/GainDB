"""Entry point for `python -m gui`.

Clean-room PySide6 front-end for the MP3 gain tool.
No VB6 source code is reused here.
"""
from __future__ import annotations

import sys

from PySide6.QtGui import QFont, QFontInfo
from PySide6.QtWidgets import QApplication

from gui.main_window import MainWindow


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
    _apply_platform_font(app)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
