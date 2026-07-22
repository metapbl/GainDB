r"""gui/dialogs/logs_dialog.py — 로그 설정 다이얼로그(원본 MP3GainGUI frmLogs 재현).

원본 frmLogs 는 "Options → Logs..." 로 여는 창으로, Error/Analysis/Change 세
로그의 파일 경로를 지정한다(clean-room, 화면 구성·동작만 관찰 차용).

원본과의 확정된 차이(합의, CLAUDE.md 10.2 — A안): 원본은 체크박스를 숨기고
"경로 유무"로 on/off 를 판정하나, 우리는 원본에 실재하는(숨겨졌던) 체크박스를
노출해 on/off(체크박스)와 위치(경로)를 분리한다. 이로써 로그를 잠깐 꺼도 경로가
사라지지 않고, on/off 상태가 화면에 드러난다.

각 행 구성: [☑ 체크박스 라벨] [경로 입력칸] [Browse...]. 체크박스를 끄면 그 행의
경로칸·Browse 버튼을 비활성화하되 경로 텍스트는 유지한다. OK 시 켜진 로그의
경로가 실제로 쓰기 가능한지 검사하고(원본 CheckFile), 실패하면 경고 후 창을 닫지
않는다. 검증을 통과하면 전달받은 LogConfig 를 갱신하고 accept.

i18n: 사용자 노출 문자열은 tr() 로 감싼다(컨텍스트 "LogsDialog"). _LogRow 는
QObject 가 아니므로 부모 다이얼로그의 tr() 로 번역된 문자열을 전달받거나
self._parent.tr() 를 사용한다. 이 다이얼로그는 모달로 생성·종료되므로 생성
시점 언어로 표시되면 충분하다(실시간 LanguageChange 처리 생략).
"""

from __future__ import annotations

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QDialog, QGridLayout, QVBoxLayout, QHBoxLayout, QCheckBox, QLineEdit,
    QPushButton, QFileDialog, QMessageBox, QDialogButtonBox,
)

from gui.logging import LogConfig, check_writable


class _LogRow:
    """한 로그(체크박스+경로+Browse)를 묶은 헬퍼. 원본 frmLogs 의 한 줄 대응."""

    def __init__(self, label: str, tooltip: str, parent: QDialog):
        self.check = QCheckBox(label, parent)
        self.check.setToolTip(tooltip)
        self.edit = QLineEdit(parent)
        self.edit.setToolTip(tooltip)
        self.browse = QPushButton(QCoreApplication.translate("LogsDialog", "Browse..."), parent)
        self.check.toggled.connect(self._on_toggled)
        self.browse.clicked.connect(self._on_browse)
        self._parent = parent
        self._title = label

    def _on_toggled(self, checked: bool):
        # 껐을 때 경로 텍스트는 유지하되 편집·Browse 만 잠근다(A안 핵심 장점).
        self.edit.setEnabled(checked)
        self.browse.setEnabled(checked)

    def _on_browse(self):
        start = self.edit.text().strip()
        caption = QCoreApplication.translate("LogsDialog", "Choose %1 file").arg(self._title)
        path, _ = QFileDialog.getSaveFileName(
            self._parent, caption, start, self._parent.log_filter())
        if path:
            self.edit.setText(path)

    def set_state(self, enabled: bool, path: str):
        self.edit.setText(path or "")
        self.check.setChecked(bool(enabled))
        # toggled 가 위에서 활성 상태를 맞추지만, 초기 unchecked→unchecked 로
        # 신호가 안 올 수 있어 명시적으로 한 번 더 반영.
        self.edit.setEnabled(bool(enabled))
        self.browse.setEnabled(bool(enabled))

    @property
    def enabled(self) -> bool:
        return self.check.isChecked()

    @property
    def path(self) -> str:
        return self.edit.text().strip()


class LogsDialog(QDialog):
    """로그 경로·on/off 를 편집하는 모달 다이얼로그(원본 frmLogs)."""

    def __init__(self, config: LogConfig, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Log options"))
        self._config = config

        layout = QVBoxLayout(self)
        grid = QGridLayout()

        self._error = _LogRow(
            self.tr("Error Log"),
            self.tr("Errors during processing are logged to this file"),
            self)
        self._analysis = _LogRow(
            self.tr("Analysis Log"),
            self.tr("Analysis results are logged to this file"), self)
        self._change = _LogRow(
            self.tr("Change Log"),
            self.tr("Gain changes are logged to this file"), self)

        for row, lr in enumerate((self._error, self._analysis, self._change)):
            grid.addWidget(lr.check, row, 0)
            grid.addWidget(lr.edit, row, 1)
            grid.addWidget(lr.browse, row, 2)
        grid.setColumnStretch(1, 1)
        layout.addLayout(grid)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok
            | QDialogButtonBox.StandardButton.Cancel,
            self)
        buttons.accepted.connect(self._on_ok)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self._load_from_config()
        self.resize(560, 160)

    def log_filter(self) -> str:
        """파일 선택 대화상자 필터(번역 대상). _LogRow 에서 호출."""
        return self.tr("Log files (*.log);;Text files (*.txt);;All files (*.*)")

    def _load_from_config(self):
        c = self._config
        self._error.set_state(c.error_enabled, c.error_path)
        self._analysis.set_state(c.analysis_enabled, c.analysis_path)
        self._change.set_state(c.change_enabled, c.change_path)

    def _on_ok(self):
        # 켜진 로그마다 경로가 비어있지 않은지 + 쓰기 가능한지 검사(원본 CheckFile).
        checks = (
            (self._error, self.tr("Error Log is enabled but no file path is set."),
             self.tr("Can't open or write to the Error log file:")),
            (self._analysis, self.tr("Analysis Log is enabled but no file path is set."),
             self.tr("Can't open or write to the Analysis log file:")),
            (self._change, self.tr("Change Log is enabled but no file path is set."),
             self.tr("Can't open or write to the Change log file:")),
        )
        title = self.tr("Log options")
        for lr, empty_msg, write_msg in checks:
            if lr.enabled:
                if not lr.path:
                    QMessageBox.warning(self, title, empty_msg)
                    return
                if not check_writable(lr.path):
                    QMessageBox.warning(self, title, f"{write_msg}\n{lr.path}")
                    return

        c = self._config
        c.error_enabled = self._error.enabled
        c.error_path = self._error.path
        c.analysis_enabled = self._analysis.enabled
        c.analysis_path = self._analysis.path
        c.change_enabled = self._change.enabled
        c.change_path = self._change.path
        self.accept()
