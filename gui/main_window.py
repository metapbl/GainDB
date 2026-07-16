"""gui/main_window.py — 메인 창(8단계 MVP 골격).

원본 MP3GainGUI frmMain 의 화면 구성·동작을 관찰해 독립 구현한다(clean-room).
이 단계(순서 2)는 골격만 만든다: 창·툴바·목표입력·테이블뷰·상태바·진행률과,
파일/폴더 추가(버튼 + 드래그앤드롭)·Clear 까지. Track Analysis/Track Gain 은
배선만 해두고 실제 분석·적용(워커)은 다음 단계에서 붙인다.

GUI 무계산 원칙: 수치는 gaindb.api 가 계산한 것만 표시한다. 여기서는 아직
api 를 호출하지 않는다(다음 단계).
"""

from __future__ import annotations

import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QTableView, QToolBar, QProgressBar, QPushButton, QFileDialog,
    QAbstractItemView, QHeaderView,
)
from PySide6.QtGui import QAction

from gui.model import FileTableModel
from gui.columns import Col
from gaindb.api import DEFAULT_TARGET_DB


def collect_mp3_paths(paths, recurse: bool = True) -> list[str]:
    """파일/폴더 경로 목록에서 .mp3 파일 경로를 모아 돌려준다.

    - 파일이면 확장자가 .mp3 일 때만 포함.
    - 폴더면 그 안의 .mp3 를 모으고, recurse 면 하위 폴더까지 훑는다
      (원본 mnuAddSubs 기본 켜짐 동작 재현).
    반환은 절대경로, 발견 순서 유지. 중복 제거는 모델(add_paths)이 담당.
    """
    result: list[str] = []
    for p in paths:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            if p.lower().endswith(".mp3"):
                result.append(p)
        elif os.path.isdir(p):
            if recurse:
                for root, _dirs, files in os.walk(p):
                    for name in sorted(files):
                        if name.lower().endswith(".mp3"):
                            result.append(os.path.join(root, name))
            else:
                for name in sorted(os.listdir(p)):
                    fp = os.path.join(p, name)
                    if os.path.isfile(fp) and name.lower().endswith(".mp3"):
                        result.append(fp)
    return result


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gain dB")
        self.resize(900, 560)
        self.setAcceptDrops(True)  # 창 전체에서 파일/폴더 드롭 수용

        self.model = FileTableModel(self)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._update_action_states()

    # --- UI 구성 ---

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_add_files = QAction("Add Files", self)
        self.act_add_files.triggered.connect(self._on_add_files)
        tb.addAction(self.act_add_files)

        self.act_add_folder = QAction("Add Folder", self)
        self.act_add_folder.triggered.connect(self._on_add_folder)
        tb.addAction(self.act_add_folder)

        tb.addSeparator()

        self.act_analyze = QAction("Track Analysis", self)
        self.act_analyze.triggered.connect(self._on_analyze)
        tb.addAction(self.act_analyze)

        self.act_gain = QAction("Track Gain", self)
        self.act_gain.triggered.connect(self._on_gain)
        tb.addAction(self.act_gain)

        tb.addSeparator()

        self.act_clear = QAction("Clear", self)
        self.act_clear.triggered.connect(self._on_clear)
        tb.addAction(self.act_clear)

    def _build_central(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)

        # 목표 음량 입력줄
        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target Volume:"))
        self.spin_target = QDoubleSpinBox(self)
        self.spin_target.setDecimals(1)
        self.spin_target.setSingleStep(1.0)
        self.spin_target.setRange(75.0, 105.0)  # 원본 targetChange 범위
        self.spin_target.setValue(DEFAULT_TARGET_DB)
        self.spin_target.setSuffix(" dB")
        self.spin_target.valueChanged.connect(self._on_target_changed)
        target_row.addWidget(self.spin_target)
        note = QLabel("(ReplayGain 89 dB reference, not absolute SPL)")
        note.setToolTip(
            "This target is relative to mp3gain's internal 89 dB ReplayGain "
            "reference. It is not an absolute SPL or LUFS level."
        )
        target_row.addWidget(note)
        target_row.addStretch(1)
        layout.addLayout(target_row)

        # 파일 목록 테이블
        self.table = QTableView(self)
        self.table.setModel(self.model)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            int(Col.NAME), QHeaderView.ResizeMode.Stretch)
        for c in (Col.VOLUME, Col.TRACK_GAIN, Col.CLIP, Col.MAX_AMP):
            header.setSectionResizeMode(
                int(c), QHeaderView.ResizeMode.ResizeToContents)
        # 모델 행 수 변화 시 버튼 활성/비활성 갱신
        self.model.rowsInserted.connect(self._update_action_states)
        self.model.rowsRemoved.connect(self._update_action_states)
        layout.addWidget(self.table)

        # 진행률(워커 연결은 다음 단계). 지금은 배치만.
        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        prog_row.addWidget(self.progress, 1)
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.setEnabled(False)
        prog_row.addWidget(self.btn_cancel)
        layout.addLayout(prog_row)

        self.setCentralWidget(central)

    def _build_statusbar(self):
        self.statusBar().showMessage("Ready")

    # --- 상태 갱신 ---

    def _update_action_states(self, *args):
        has_rows = self.model.rowCount() > 0
        self.act_analyze.setEnabled(has_rows)
        self.act_gain.setEnabled(has_rows)
        self.act_clear.setEnabled(has_rows)
        self.statusBar().showMessage(f"{self.model.rowCount()} file(s)")

    # --- 파일 추가 공통 ---

    def _add_from(self, paths):
        mp3s = collect_mp3_paths(paths, recurse=True)
        if not mp3s:
            self.statusBar().showMessage("No .mp3 files found")
            return
        added = self.model.add_paths(mp3s)
        self.statusBar().showMessage(
            f"Added {added} file(s), {self.model.rowCount()} total"
        )

    # --- 툴바 액션 ---

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Add MP3 files", "", "MP3 files (*.mp3);;All files (*.*)"
        )
        if files:
            self._add_from(files)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Add folder")
        if folder:
            self._add_from([folder])

    def _on_analyze(self):
        # 다음 단계(워커)에서 gaindb.api.analyze_file 로 연결.
        self.statusBar().showMessage(
            "Track Analysis will be connected in the next step."
        )

    def _on_gain(self):
        self.statusBar().showMessage(
            "Track Gain will be connected in the next step."
        )

    def _on_clear(self):
        sel = self.table.selectionModel().selectedRows()
        if sel:
            self.model.remove_rows([idx.row() for idx in sel])
        else:
            self.model.clear()

    def _on_target_changed(self, value):
        # 다음 단계에서 분석된 행에 recompute_target 을 호출해 재표시.
        self.statusBar().showMessage(f"Target set to {value:.1f} dB")

    # --- 드래그 앤 드롭(원본 lstvMain_OLEDragDrop 대응) ---

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self._add_from(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
