# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gui/dialogs/constant_gain_dialog.py - Apply Constant Gain dialog (F10, D103).

Same controls as the original mp3gain GUI: a slider of -8..+8 mp3 gain steps
with the dB value shown (1 step = 1.5 dB), and "Apply to only one channel"
with left/right. The caller applies the chosen steps without analysis.
"""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox, QDialog, QDialogButtonBox, QGridLayout, QLabel, QRadioButton,
    QSlider, QVBoxLayout,
)

from gaindb.analysis import DB_PER_STEP


class ConstantGainDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Constant Gain Change"))
        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(self.tr("Select gain change to apply to all files")))

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(-8, 8)
        self.slider.setPageStep(4)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)
        layout.addWidget(self.slider)

        values = QGridLayout()
        self.lbl_steps = QLabel()
        self.lbl_db = QLabel()
        for col, (name, value) in enumerate(((self.tr("mp3 gain"), self.lbl_steps),
                                             (self.tr("dB"), self.lbl_db))):
            values.addWidget(QLabel(name), 0, col * 2)
            values.addWidget(value, 0, col * 2 + 1)
        layout.addLayout(values)

        self.chk_one = QCheckBox(self.tr("Apply to only one channel"))
        self.rb_left = QRadioButton(self.tr("Channel 1 (Left)"))
        self.rb_right = QRadioButton(self.tr("Channel 2 (Right)"))
        self.rb_left.setChecked(True)
        layout.addSpacing(12)
        layout.addWidget(self.chk_one)
        channels = QVBoxLayout()
        channels.setContentsMargins(24, 0, 0, 0)  # 체크박스에 딸린 선택임을 들여쓰기로
        channels.addWidget(self.rb_left)
        channels.addWidget(self.rb_right)
        layout.addLayout(channels)
        self.chk_one.toggled.connect(self._sync_channel)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.slider.valueChanged.connect(self._sync_labels)
        self._sync_labels()
        self._sync_channel()

    def _sync_labels(self):
        self.lbl_steps.setText(str(self.slider.value()))
        self.lbl_db.setText(f"{self.slider.value() * DB_PER_STEP:.1f}")

    def _sync_channel(self):
        for rb in (self.rb_left, self.rb_right):
            rb.setEnabled(self.chk_one.isChecked())

    def steps(self) -> int:
        return self.slider.value()

    def channel(self) -> int | None:
        """None = both channels, 0 = left, 1 = right (CLI -l c)."""
        if not self.chk_one.isChecked():
            return None
        return 0 if self.rb_left.isChecked() else 1
