# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gui/dialogs/about_dialog.py - About dialog (independent implementation).

Shows the program name, version, a one-line description, copyright, license,
and third-party component notices (PySide6/Qt LGPLv3, NumPy/SciPy BSD, ffmpeg
external). The name and version come from gaindb.__init__ (single source of
truth); the icon comes from gui.resources.app_icon.

i18n: user-facing strings are wrapped in tr() (context "AboutDialog"). License
names (Apache License 2.0, LGPL v3, BSD 3-Clause) and bundled file names
(LICENSE, NOTICE, THIRD_PARTY_LICENSES) are proper nouns and stay verbatim even
in translation. The dialog is created/destroyed modally, so it is shown in the
language in effect at creation time (no live LanguageChange handling needed).
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QDialogButtonBox,
)

from gaindb import __version__, PROGNAME
from gui.resources import app_icon

# Project homepage (shown as a clickable link in the About body).
_HOMEPAGE_URL = "https://github.com/metapbl/GainDB"


class AboutDialog(QDialog):
    """Modal About dialog: program info + license + third-party notices."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("About %1").replace("%1", PROGNAME))

        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Header: icon + name/version ---
        header = QHBoxLayout()
        header.setSpacing(12)

        icon = app_icon()
        if not icon.isNull():
            icon_label = QLabel(self)
            icon_label.setPixmap(icon.pixmap(64, 64))
            icon_label.setAlignment(Qt.AlignmentFlag.AlignTop)
            header.addWidget(icon_label)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        name_label = QLabel(f"<b><span style='font-size:16pt'>{PROGNAME}</span></b>",
                            self)
        title_box.addWidget(name_label)
        version_label = QLabel(
            self.tr("Version %1").replace("%1", __version__), self)
        title_box.addWidget(version_label)
        title_box.addStretch(1)
        header.addLayout(title_box)
        header.addStretch(1)
        layout.addLayout(header)

        # --- Description ---
        desc = QLabel(self.tr(
            "This program is an independent Python implementation of the "
            "ReplayGain algorithm, producing gain results compatible with "
            "mp3gain."
        ), self)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        # --- Copyright + license ---
        copyright_label = QLabel(
            "\u00a9 2026 META PUBLIC\n"
            + self.tr("Licensed under the Apache License, Version 2.0."),
            self)
        copyright_label.setWordWrap(True)
        layout.addWidget(copyright_label)

        # --- Third-party notices ---
        # License names / file names stay verbatim (proper nouns); only the
        # surrounding sentence structure is translatable.
        third_party = QLabel(
            self.tr("Third-party components:") + "\n"
            + "  \u2022 PySide6 / Qt \u2014 "
            + self.tr("used under the GNU LGPL v3") + "\n"
            + "  \u2022 NumPy, SciPy \u2014 "
            + self.tr("used under the BSD 3-Clause License") + "\n"
            + "  \u2022 ffmpeg \u2014 "
            + self.tr("used as an external tool (called from PATH, not "
                      "bundled) when installed"),
            self)
        third_party.setWordWrap(True)
        layout.addWidget(third_party)

        files_label = QLabel(self.tr(
            "For full license texts, see the LICENSE, NOTICE, and "
            "THIRD_PARTY_LICENSES files included with this program."
        ), self)
        files_label.setWordWrap(True)
        layout.addWidget(files_label)

        # --- Homepage link ---
        link_label = QLabel(
            f'<a href="{_HOMEPAGE_URL}">{_HOMEPAGE_URL}</a>', self)
        link_label.setOpenExternalLinks(True)
        link_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextBrowserInteraction)
        layout.addWidget(link_label)

        # --- Close button ---
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Close, self)
        buttons.rejected.connect(self.reject)
        buttons.accepted.connect(self.accept)
        buttons.clicked.connect(lambda _btn: self.accept())
        layout.addWidget(buttons)

        self.setMinimumWidth(460)