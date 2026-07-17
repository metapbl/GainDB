"""gui/main_window.py — 메인 창(8단계 MVP + 태그 스캔 워커 + Analysis/Gain 워커).

원본 MP3GainGUI frmMain 의 화면 구성·동작을 관찰해 독립 구현한다(clean-room).
파일/폴더 추가(버튼 + 드래그앤드롭)·Clear·헤더 클릭 자연 정렬·Delete 키 선택
삭제·더블클릭 재생에 더해, 파일 추가 시 태그를 백그라운드 워커로 읽어 표시
(원본 AddSingleFile), Track Analysis 와 Track Gain 도 QThread 워커로 연결한다.

태그 스캔 워커화(대량 추가 프리징 해소): 파일 추가 시 행은 메인에서 즉시 만들고
(빈칸 상태로 목록에 바로 보임), 태그는 TagScanWorker 가 백그라운드로 채운다.
스캔 진행 중에는 겸용 버튼이 Pause 로, 멈춘 뒤 미스캔(pending) 행이 남으면
Rescan 으로 바뀐다(같은 자리에서 상태 전환). Track Analysis/Track Gain 진행
중에는 같은 버튼이 Cancel 이다(작업 성격상 이어가기 개념이 없어 Rescan 없음).

작업 중 상태바에는 "작업 k/N — 파일명"을 표시한다(current 시그널; 경로 없이
basename 만 — 전체 경로는 리스트 행 툴팁으로 확인 가능).

Path\File 컬럼은 PathElideDelegate 로 그린다: 경로를 먼저 접고(C:\…\MUSIC\)
파일명을 최후까지 보존하며, 그래도 좁으면 그때만 파일명을 elide 한다.

겸용 버튼(진행바 옆) 규칙 — _update_action_states 에서 결정:
  - 태그 스캔 워커 실행 중          → "Pause" (활성)   : 파일 경계에서 스캔 중단
  - 분석/적용 워커 실행 중          → "Cancel"(활성)   : 파일 경계에서 작업 중단
  - 멈춤 + 미스캔(pending) 행 있음  → "Rescan"(활성)   : 남은 pending 이어 스캔
  - 멈춤 + pending 없음             → "Cancel"(비활성) : 동작 없음(기본 상태)
클릭 핸들러는 하나이며 위 상태에 따라 pause/cancel/rescan 으로 분기한다.

Track Gain(원본 RadioGain 재현): 대상 행마다 (a) 미분석이면 먼저 분석 →
(b) 변동 스텝이 0 이면 분석까지만 → (c) 스텝이 있으면 실제 적용. 이 판단·
수행은 전부 ApplyWorker(QThread) 안에서 이루어진다(분석·적용 모두 무겁다).

GUI 무계산 원칙: 수치는 gaindb.api 가 계산한 것만 표시한다.
정렬 순서는 프록시(뷰) 좌표, 실제 데이터는 원본 모델 좌표이므로
삭제·더블클릭·워커 결과 반영 시 반드시 좌표를 구분한다.

워커 규칙: 무거운 작업(ffmpeg 디코딩·파일 적용)은 워커에서 돌리고,
워커는 시그널만 방출한다. 모델 변경은 전부 메인 스레드의 슬롯에서 수행한다.
태그 스캔도 워커로 돌리되(대량 추가 프리징 해소) 워커는 읽기만 하고 모델
변경은 메인 슬롯이 담당한다.
"""

from __future__ import annotations

import os
import subprocess
import sys

from PySide6.QtCore import (
    Qt, QSortFilterProxyModel, QCollator, QModelIndex, Signal, QRect, QPoint,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QTableView, QToolBar, QProgressBar, QPushButton, QFileDialog,
    QAbstractItemView, QHeaderView, QRubberBand, QStyledItemDelegate,
)

from PySide6.QtGui import QAction, QKeySequence

from gui.model import FileTableModel, SORT_ROLE
from gui.columns import Col
from gui.workers import TagScanWorker, AnalyzeWorker, ApplyWorker
from gaindb.api import DEFAULT_TARGET_DB, recompute_target


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


def open_with_default_app(path: str) -> None:
    """OS 기본 앱으로 파일을 연다(원본 lstvMain_DblClick 의 ShellExecute 대응).

    플랫폼별 분기: Windows=os.startfile, macOS=open, Linux=xdg-open.
    실패해도 예외를 올리지 않고 호출자가 상태바로 안내하도록 예외를 전파한다.
    """
    if sys.platform.startswith("win"):
        os.startfile(path)  # type: ignore[attr-defined]  # Windows 전용
    elif sys.platform == "darwin":
        subprocess.run(["open", path], check=False)
    else:
        subprocess.run(["xdg-open", path], check=False)


class PathElideDelegate(QStyledItemDelegate):
    """Path\\File 컬럼 전용 델리게이트: 경로를 먼저 접고 파일명을 최후까지 보존.

    표준 elide 모드(ElideLeft/Middle/Right)는 문자열을 한 지점에서만 접어
    "경로만 접고 파일명은 보존, 그래도 좁으면 파일명 자름"이라는 2단계 규칙을
    표현할 수 없다. 그래서 직접 그린다. 셀 폭에 맞춰 단계적으로 축소한다:

      1) 전체 경로가 다 들어가면 그대로.
      2) 안 들어가면 경로를 접는다: 드라이브(첫 요소) + \\…\\ + 마지막 폴더 +
         \\ + 파일명. 예: C:\\Users\\...\\MUSIC\\104.mp3 → C:\\…\\MUSIC\\104.mp3.
      3) 그렇게 최소로 접어도 넘치면, 그때만 파일명을 뒤에서 elide 한다
         (C:\\…\\MUSIC\\some very long na…). 즉 파일명이 최후까지 보호된다.

    그리기만 커스터마이즈하고 배경·선택 하이라이트는 기본 스타일에 맡겨
    다크테마 팔레트(진척 11)를 깨지 않는다. 전체 경로 툴팁·정렬은 모델의
    ToolTipRole·SORT_ROLE 이 그대로 담당하므로 여기서 건드리지 않는다.
    """

    _SEP = "\u2026"  # '…' (한 글자 말줄임표)

    def _elide_path(self, text: str, avail: int, fm) -> str:
        """text(전체 경로)를 폭 avail(px)에 맞춰 단계적으로 축소한 문자열."""
        # 1) 다 들어가면 그대로.
        if fm.horizontalAdvance(text) <= avail:
            return text

        # 경로를 구분자로 분해. 이 앱은 Windows 절대경로(\\)를 저장한다.
        sep = "\\" if "\\" in text else "/"
        parts = text.split(sep)
        # parts = [드라이브(또는 첫 요소), ..., 마지막폴더, 파일명]
        if len(parts) >= 3:
            drive = parts[0]
            filename = parts[-1]
            last_dir = parts[-2]
            # 2) 경로 접기: 드라이브\…\마지막폴더\파일명.
            folded = f"{drive}{sep}{self._SEP}{sep}{last_dir}{sep}{filename}"
            if fm.horizontalAdvance(folded) <= avail:
                return folded
            # 3) 최소로 접어도 넘침: 파일명만 뒤에서 elide.
            prefix = f"{drive}{sep}{self._SEP}{sep}{last_dir}{sep}"
            prefix_w = fm.horizontalAdvance(prefix)
            remain = avail - prefix_w
            if remain <= 0:
                # 접두조차 안 들어갈 만큼 극단적으로 좁으면 전체를 좌측 elide.
                return fm.elidedText(text, Qt.TextElideMode.ElideLeft, avail)
            elided_name = fm.elidedText(
                filename, Qt.TextElideMode.ElideRight, remain)
            return prefix + elided_name

        # 경로 요소가 2개 이하(예외적)면 좌측 elide 로 파일명 우선 노출.
        return fm.elidedText(text, Qt.TextElideMode.ElideLeft, avail)

    def paint(self, painter, option, index):
        from PySide6.QtWidgets import QStyle, QApplication

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        opt = self.initStyleOption_copy(option, index)
        opt.text = ""  # 기본 컨트롤이 텍스트를 그리지 않도록 비운다.
        style = opt.widget.style() if opt.widget else QApplication.style()
        style.drawControl(QStyle.ControlElement.CE_ItemViewItem, opt, painter,
                          opt.widget)

        text_rect = style.subElementRect(
            QStyle.SubElement.SE_ItemViewItemText, opt, opt.widget)
        fm = opt.fontMetrics
        avail = text_rect.width() - 4
        shown = self._elide_path(str(text), max(avail, 0), fm)

        if opt.state & QStyle.StateFlag.State_Selected:
            color = opt.palette.highlightedText().color()
        else:
            color = opt.palette.text().color()
        painter.save()
        painter.setPen(color)
        painter.drawText(
            text_rect.adjusted(2, 0, -2, 0),
            int(Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft),
            shown,
        )
        painter.restore()

    def initStyleOption_copy(self, option, index):
        """option 을 복사·초기화해 반환(원본 option 을 변형하지 않기 위해)."""
        from PySide6.QtWidgets import QStyleOptionViewItem
        opt = QStyleOptionViewItem(option)
        self.initStyleOption(opt, index)
        return opt


class FileTableView(QTableView):
    """Delete 키 삭제 + 빈 영역 고무줄(사각형) 선택을 지원하는 QTableView.

    - Delete 키(원본 lstvMain_KeyDown, KeyCode 46 → ClearFiles): 선택 행만 삭제
      요청 시그널을 낸다. 테이블 포커스 시에만 동작한다(전역 아님).
    - 빈 영역 고무줄 선택(원본 lstvMain 의 rubber-band): 행이 없는 여백에서
      좌클릭 드래그를 시작하면 사각형을 그려 겹치는 행을 선택한다. QTableView 는
      QListView/QTreeView 와 달리 setSelectionRectVisible 이 없어 직접 구현한다.
      행 위에서 시작한 클릭·드래그는 고무줄에 개입하지 않고 QTableView 기본
      동작(클릭 선택·행 드래그 선택·더블클릭)에 위임한다.
    - Ctrl+A 전체선택·doubleClicked 는 QTableView 기본 동작이라 손대지 않는다.
    """

    delete_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rubber_band: QRubberBand | None = None
        self._rubber_origin = QPoint()
        self._rubber_active = False
        self._rubber_additive = False  # Ctrl 로 시작하면 기존 선택에 추가

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_requested.emit()
            event.accept()
            return
        super().keyPressEvent(event)

    def mousePressEvent(self, event):
        # 좌클릭이고 빈 영역(행 없음)에서 시작할 때만 고무줄 선택 개시.
        if event.button() == Qt.MouseButton.LeftButton:
            index = self.indexAt(event.position().toPoint())
            if not index.isValid():
                self._rubber_active = True
                self._rubber_origin = event.position().toPoint()
                self._rubber_additive = bool(
                    event.modifiers() & Qt.KeyboardModifier.ControlModifier
                )
                if self._rubber_band is None:
                    self._rubber_band = QRubberBand(
                        QRubberBand.Shape.Rectangle, self.viewport()
                    )
                self._rubber_band.setGeometry(
                    QRect(self._rubber_origin, self._rubber_origin))
                self._rubber_band.show()
                # Ctrl 이 아니면 기존 선택을 비운다(새 선택 시작).
                if not self._rubber_additive:
                    self.clearSelection()
                event.accept()
                return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._rubber_active and self._rubber_band is not None:
            pos = event.position().toPoint()
            rect = QRect(self._rubber_origin, pos).normalized()
            self._rubber_band.setGeometry(rect)
            self._select_in_rect(rect)
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._rubber_active and event.button() == Qt.MouseButton.LeftButton:
            self._rubber_active = False
            if self._rubber_band is not None:
                self._rubber_band.hide()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def _select_in_rect(self, rect: QRect):
        """뷰포트 좌표 사각형 rect 에 걸치는 행을 선택한다.

        각 행의 첫 열 셀 사각형이 rect 와 겹치면 그 행을 선택 집합에 넣는다.
        additive(Ctrl 시작)면 드래그 시작 시점의 선택 위에 더해지도록, 매번
        rect 기준 새 선택을 계산해 반영한다(간단·예측 가능). 행 선택 모드라
        한 행만 골라도 행 전체가 선택된다.
        """
        sel_model = self.selectionModel()
        model = self.model()
        if model is None:
            return

        from PySide6.QtCore import QItemSelection, QItemSelectionModel

        selection = QItemSelection()
        last_col = model.columnCount() - 1
        for r in range(model.rowCount()):
            row_rect = self.visualRect(model.index(r, 0))
            # 세로로 겹치면 그 행이 사각형에 걸친 것으로 본다(가로 전체 행 선택).
            if row_rect.top() <= rect.bottom() and row_rect.bottom() >= rect.top():
                left = model.index(r, 0)
                right = model.index(r, last_col)
                selection.select(left, right)

        if self._rubber_additive:
            sel_model.select(
                selection,
                QItemSelectionModel.SelectionFlag.Select
                | QItemSelectionModel.SelectionFlag.Rows,
            )
        else:
            sel_model.select(
                selection,
                QItemSelectionModel.SelectionFlag.ClearAndSelect
                | QItemSelectionModel.SelectionFlag.Rows,
            )


class NaturalSortProxy(QSortFilterProxyModel):
    """Windows 11 탐색기식 자연 정렬 프록시.

    - 문자열(파일명, clip 상태): QCollator 로 숫자 부분을 실제 크기 비교.
    - 숫자(volume, track gain, curr max amp): 값 그대로 비교.
    - None(미분석): 정렬 방향과 무관하게 항상 맨 아래로(결측 처리).
    원본 typed 값은 SORT_ROLE 로 받는다(표시 문자열이 아니라).
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)
        self._collator = QCollator()
        self._collator.setNumericMode(True)
        self._collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = self.sourceModel().data(left, SORT_ROLE)
        rv = self.sourceModel().data(right, SORT_ROLE)

        # 미분석(None)은 항상 뒤로. sortOrder 를 보정해 방향과 무관하게 처리.
        if lv is None and rv is None:
            return False
        descending = self.sortOrder() == Qt.SortOrder.DescendingOrder
        if lv is None:
            return descending      # 내림차순이면 "작다"로 취급해 아래로
        if rv is None:
            return not descending  # 오름차순이면 좌측이 위, None(우측)은 아래

        # 문자열은 자연 정렬, 그 외는 값 비교.
        if isinstance(lv, str) or isinstance(rv, str):
            return self._collator.compare(str(lv), str(rv)) < 0
        return lv < rv


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gain dB")
        self.resize(900, 560)
        self.setAcceptDrops(True)  # 창 전체에서 파일/폴더 드롭 수용

        self.model = FileTableModel(self)
        self.proxy = NaturalSortProxy(self)
        self.proxy.setSourceModel(self.model)

        # 실행 중 워커 보유(GC 방지). 한 번에 한 종류만 돈다(busy 잠금).
        # _worker_kind: "scan" | "analyze" | "apply" | None.
        #   겸용 버튼(Pause/Cancel/Rescan) 텍스트·동작이 이 종류에 따라 갈린다.
        self._worker: TagScanWorker | AnalyzeWorker | ApplyWorker | None = None
        self._worker_kind: str | None = None
        self._scanned_count = 0    # 이번 태그 스캔에서 처리한 개수
        self._scan_offset = 0      # 이번 스캔 시작 시점에 이미 스캔돼 있던 행 수
                                   # (전체 목록 대비 누적 진행바 계산용 오프셋)
        self._scan_total = 0       # 이번 스캔의 전체 분모(상태바 표시용)
        self._analyzed_count = 0   # 이번 작업에서 분석/적용 성공 개수
        self._applied_count = 0    # 이번 Track Gain 에서 실제 적용된 개수
        self._failed_count = 0     # 이번 작업에서 실패한 개수
        self._batch_total = 0      # 이번 분석/적용 작업의 대상 수(상태바 표시용)

        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._update_action_states()

    # --- UI 구성 ---

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        # 단축키는 원본 mp3gain 메뉴(frmMain.frm)를 재현: Add Files=Ctrl+F,
        # Add Folder=Ctrl+D, Track Analysis=Ctrl+T, Track Gain=Ctrl+G.
        # Clear 는 원본에 전용 단축키가 없어(원본은 Delete=선택삭제만) 편의로
        # Ctrl+Shift+Delete 를 붙였다(전체 삭제=파괴적이라 오발 방지 위해 3키
        # 조합, 사용자 합의). 툴팁에 단축키를 표기한다. busy 시에는
        # _update_action_states 가 QAction 을 비활성화해 단축키도 함께 막힌다.

        self.act_add_files = QAction("Add Files", self)
        self.act_add_files.setShortcut(QKeySequence("Ctrl+F"))
        self.act_add_files.setToolTip("Add MP3 files to the list (Ctrl+F)")
        self.act_add_files.triggered.connect(self._on_add_files)
        tb.addAction(self.act_add_files)

        self.act_add_folder = QAction("Add Folder", self)
        self.act_add_folder.setShortcut(QKeySequence("Ctrl+D"))
        self.act_add_folder.setToolTip("Add all MP3 files in a folder (Ctrl+D)")
        self.act_add_folder.triggered.connect(self._on_add_folder)
        tb.addAction(self.act_add_folder)

        tb.addSeparator()

        self.act_analyze = QAction("Track Analysis", self)
        self.act_analyze.setShortcut(QKeySequence("Ctrl+T"))
        self.act_analyze.setToolTip("Analyze track gain without applying (Ctrl+T)")
        self.act_analyze.triggered.connect(self._on_analyze)
        tb.addAction(self.act_analyze)

        self.act_gain = QAction("Track Gain", self)
        self.act_gain.setShortcut(QKeySequence("Ctrl+G"))
        self.act_gain.setToolTip("Apply track gain to files (Ctrl+G)")
        self.act_gain.triggered.connect(self._on_gain)
        tb.addAction(self.act_gain)

        tb.addSeparator()

        self.act_clear = QAction("Clear", self)
        self.act_clear.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
        self.act_clear.setToolTip(
            "Clear all files from the list (Ctrl+Shift+Delete)"
        )
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

        # 파일 목록 테이블 (프록시 경유, Delete 키 + 더블클릭 재생 지원)
        self.table = FileTableView(self)
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)  # 헤더 클릭 정렬
        # Path\File 컬럼은 전용 델리게이트로 그린다: 경로를 먼저 접고
        # (C:\…\MUSIC\) 파일명을 최후까지 보존, 그래도 좁으면 파일명 elide.
        # 창을 넓히면 접혔던 경로가 다시 드러난다. 전체 경로는 행 툴팁으로 확인.
        self.table.setItemDelegateForColumn(
            int(Col.NAME), PathElideDelegate(self.table))
        # 데이터 행 높이를 촘촘하게(가로 헤더 높이는 별개라 영향 없음).
        self.table.verticalHeader().setDefaultSectionSize(22)
        # 초기 정렬: Path\File 기준 오름차순(헤더 화살표와 상태 일치).
        self.table.sortByColumn(int(Col.NAME), Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.delete_requested.connect(self._on_delete_selected)
        self.table.doubleClicked.connect(self._on_double_click)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            int(Col.NAME), QHeaderView.ResizeMode.Stretch)
        for c in (Col.VOLUME, Col.TRACK_GAIN, Col.CLIP, Col.MAX_AMP):
            header.setSectionResizeMode(
                int(c), QHeaderView.ResizeMode.ResizeToContents)
        # 모델 행 수 변화 시 버튼 활성/비활성 갱신
        self.model.rowsInserted.connect(self._update_action_states)
        self.model.rowsRemoved.connect(self._update_action_states)
        self.model.modelReset.connect(self._update_action_states)
        layout.addWidget(self.table)

        # 진행률
        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        prog_row.addWidget(self.progress, 1)
        # 겸용 버튼: 상태에 따라 Pause / Cancel / Rescan 으로 바뀐다.
        # 클릭 핸들러는 하나(_on_action_button)이며 내부에서 분기한다.
        self.btn_action = QPushButton("Cancel", self)
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self._on_action_button)
        prog_row.addWidget(self.btn_action)
        layout.addLayout(prog_row)

        self.setCentralWidget(central)

    def _build_statusbar(self):
        self.statusBar().showMessage("Ready")

    # --- 상태 갱신 ---

    def _is_busy(self) -> bool:
        # isRunning()은 start() 직후 아직 False 일 수 있어(스레드 기동 지연)
        # 그 짧은 창에 버튼이 Rescan 으로 잘못 그려졌다. 워커 객체 존재 여부로
        # 판정한다 — _on_*_finished 가 _worker=None 을 하므로 이게 안정적이다.
        return self._worker is not None

    def _has_pending(self) -> bool:
        """목록에 태그 스캔 미시도(Rescan 대상) 행이 하나라도 있는지.

        태그 스캔을 아직 시도하지 않은 행(needs_tag_scan)이 Rescan 대상이다.
        태그가 없어서 값이 없는 행은 이미 스캔을 시도했으므로 대상이 아니다
        (그런 행은 Track Analysis 로 값을 채운다).
        """
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is not None and fr.needs_tag_scan():
                return True
        return False

    def _update_action_states(self, *args):
        busy = self._is_busy()
        has_rows = self.model.rowCount() > 0
        # 워커 실행 중에는 파일 추가·분석·적용·Clear 를 잠근다.
        self.act_add_files.setEnabled(not busy)
        self.act_add_folder.setEnabled(not busy)
        self.act_analyze.setEnabled(has_rows and not busy)
        self.act_gain.setEnabled(has_rows and not busy)
        self.act_clear.setEnabled(has_rows and not busy)

        # 겸용 버튼 텍스트·활성 결정(설계 표 그대로):
        #   태그 스캔 중  → Pause(활성)
        #   분석/적용 중  → Cancel(활성)
        #   멈춤+pending  → Rescan(활성)
        #   멈춤+무pending→ Cancel(비활성)
        if busy:
            if self._worker_kind == "scan":
                self.btn_action.setText("Pause")
            else:
                self.btn_action.setText("Cancel")
            self.btn_action.setEnabled(True)
        else:
            if self._has_pending():
                self.btn_action.setText("Rescan")
                self.btn_action.setEnabled(True)
            else:
                self.btn_action.setText("Cancel")
                self.btn_action.setEnabled(False)

        if not busy:
            self.statusBar().showMessage(f"{self.model.rowCount()} file(s)")

    # --- 겸용 버튼 클릭(Pause / Cancel / Rescan 분기) ---

    def _on_action_button(self):
        """진행바 옆 겸용 버튼. 현재 상태에 따라 pause/cancel/rescan.

        - 태그 스캔 실행 중  : Pause  → 스캔 중단 요청(파일 경계에서 멈춤).
        - 분석/적용 실행 중  : Cancel → 작업 중단 요청(파일 경계에서 멈춤).
        - 멈춤 + pending 있음 : Rescan → 남은 pending 행을 이어서 태그 스캔.
        """
        if self._is_busy():
            # 실행 중이면 종류 불문 중단 요청(Pause/Cancel 동작은 동일).
            if self._worker is not None:
                self._worker.request_cancel()
                self.btn_action.setEnabled(False)
                if self._worker_kind == "scan":
                    self.statusBar().showMessage("Pausing after current file...")
                else:
                    self.statusBar().showMessage(
                        "Cancelling after current file...")
            return
        # 멈춰 있으면 Rescan: pending 행 태그 스캔 재개.
        self._start_tag_scan(self._pending_paths())

    # --- 대상 행 결정 ---

    def _pending_paths(self) -> list[str]:
        """태그 스캔 미시도(Rescan 대상) 행들의 경로. Rescan/최초 스캔의 대상.

        needs_tag_scan()==True 인 행만 모은다. 이로써 Rescan 은 이미 스캔한
        행(태그 있든 없든)을 건너뛰고 중단 지점부터 이어간다.
        """
        paths = []
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is not None and fr.needs_tag_scan():
                paths.append(fr.path)
        return paths

    def _target_source_rows(self) -> list[int]:
        """작업 대상 모델 행 인덱스. 선택 행이 있으면 그것, 없으면 전체.

        선택 인덱스는 프록시(뷰) 좌표이므로 mapToSource 로 원본 모델 행으로
        변환한다.
        """
        sel = self.table.selectionModel().selectedRows()
        if sel:
            return [self.proxy.mapToSource(idx).row() for idx in sel]
        return list(range(self.model.row_count()))

    def _selected_source_rows(self) -> list[int]:
        """선택된 행의 원본 모델 인덱스만 반환(선택 없으면 빈 리스트)."""
        sel = self.table.selectionModel().selectedRows()
        return [self.proxy.mapToSource(idx).row() for idx in sel]

    # --- 태그 스캔 워커 시작(최초 추가 후 · Rescan 공용) ---

    def _start_tag_scan(self, paths: list[str]):
        """주어진 경로들의 태그를 백그라운드로 스캔한다(원본 AddSingleFile).

        최초 추가 직후와 Rescan/추가가 이 함수를 공유한다. 이미 워커가 돌고
        있으면 무시한다(busy 잠금). 대상이 없으면 아무 것도 안 한다.

        진행바는 "전체 목록 대비 누적" 기준이다(태그 스캔만의 방식 — Pause/
        Rescan 으로 이어가므로). 범위 = 전체 행 수, 오프셋 = 이번 스캔 시작
        시점에 이미 스캔돼 있던 행 수(전체 − 이번 대상). 진행 시 오프셋을
        더한 값을 표시해, 재개·추가가 전체에서 이어지는 것이 드러난다.
        """
        if self._is_busy() or not paths:
            self._update_action_states()
            return
        target_db = self.spin_target.value()
        total = self.model.row_count()
        self._scan_offset = total - len(paths)  # 이미 스캔된 행 수
        self._scan_total = total
        self._scanned_count = 0
        self._worker = TagScanWorker(paths, target_db, self)
        self._worker_kind = "scan"
        self._worker.current.connect(self._on_scan_current)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.row_done.connect(self._on_scan_row_done)
        self._worker.done.connect(self._on_scan_finished)

        self.progress.setRange(0, total)
        self.progress.setValue(self._scan_offset)  # 이미 스캔된 만큼 채우고 시작
        self._update_action_states()  # 버튼을 Pause 로
        self.statusBar().showMessage(
            f"Scanning tags {self._scan_offset}/{total}")
        self._worker.start()

    # --- 파일 추가 공통 (행 즉시 추가 → 태그는 워커로 백그라운드 스캔) ---

    def _add_from(self, paths):
        if self._is_busy():
            self.statusBar().showMessage("Busy — wait for the current task")
            return
        mp3s = collect_mp3_paths(paths, recurse=True)
        if not mp3s:
            self.statusBar().showMessage("No .mp3 files found")
            return
        new_rows = self.model.add_paths(mp3s)  # 추가된 모델 행(빈칸 상태로 즉시 표시)
        if not new_rows:
            self.statusBar().showMessage(
                f"No new files, {self.model.rowCount()} total"
            )
            return
        # 원본 AddSingleFile 대응: 태그 조회를 백그라운드 워커로 돌린다. 새로
        # 추가된 행뿐 아니라 이전 Pause 로 남은 미스캔 행까지 함께 이어 스캔
        # 하도록 _pending_paths()(전체 미스캔)를 대상으로 넘긴다. 진행바는
        # _start_tag_scan 이 전체 목록 기준으로 다시 잡으므로, 추가된 만큼
        # 분모가 커지고 이미 스캔된 만큼 채운 채 시작한다.
        self.statusBar().showMessage(
            f"Added {len(new_rows)} file(s), {self.model.rowCount()} total — "
            f"scanning tags..."
        )
        self._start_tag_scan(self._pending_paths())

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
        if self._is_busy():
            return

        # 대상 행 중 "값이 아직 없는" 것만 분석한다(원본 RadiodBGain=NOREALNUM).
        paths = []
        for r in self._target_source_rows():
            fr = self.model.get_row(r)
            if fr is not None and fr.needs_analysis():
                paths.append(fr.path)

        if not paths:
            self.statusBar().showMessage(
                "Nothing to analyze (all selected files already have values)"
            )
            return

        target_db = self.spin_target.value()
        self._analyzed_count = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._worker = AnalyzeWorker(paths, target_db, self)
        self._worker_kind = "analyze"
        self._worker.current.connect(self._on_analyze_current)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.row_done.connect(self._on_worker_row_done)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_worker_finished)

        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self._update_action_states()  # 버튼을 Cancel 로
        self.statusBar().showMessage(f"Analyzing {len(paths)} file(s)...")
        self._worker.start()

    def _on_gain(self):
        """Track Gain 적용(원본 RadioGain 재현). ApplyWorker 로 위임한다.

        대상: 선택 있으면 선택·없으면 전체(원본 mnuSelectedFiles 분기 대응).
        단, 이미 값이 있으면서 목표까지의 스텝이 0 인 곡(이미 목표에 도달 →
        적용 불필요)은 대상·분모에서 뺀다. 원본 RadioGain 도 실제 /g 실행은
        RadioMp3Gain<>0 일 때만 하므로, "적용될 곡"만 분모로 잡는 게 원본
        동작에 맞고 진행바도 실제 작업량을 반영한다(이미 적용된 곡을 재시작
        때 다시 훑어 진행바가 중간부터 시작한 것처럼 보이던 문제도 해소).

        값이 아직 없는 곡(미분석)은 steps 를 미리 모르므로 포함한다 — 워커가
        분석 후 steps=0 이면 그때 건너뛴다(row_analyzed). 값 있는 곡은 여기서
        steps 를 알 수 있어 0 이면 미리 제외한다. 씨앗으로 각 행의 기존 result
        를 함께 넘겨 이미 값이 있으면 재분석을 피한다(원본이 RadiodBGain 보유
        시 재분석 안 함과 일치).
        """
        if self._is_busy():
            return

        rows = self._target_source_rows()
        paths = []
        seed_results = {}
        for r in rows:
            fr = self.model.get_row(r)
            if fr is None:
                continue
            res = fr.result
            if (res and res.get("status") == "ok"
                    and res.get("steps") is not None
                    and res.get("steps") == 0):
                continue
            paths.append(fr.path)
            seed_results[fr.path] = fr.result  # None 이면 워커가 분석함

        if not paths:
            self.statusBar().showMessage(
                "Nothing to apply (all target files already at target)"
            )
            return

        target_db = self.spin_target.value()
        self._analyzed_count = 0
        self._applied_count = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._worker = ApplyWorker(paths, target_db, seed_results, self)
        self._worker_kind = "apply"
        self._worker.current.connect(self._on_apply_current)
        self._worker.progress.connect(self._on_apply_progress)
        self._worker.row_analyzed.connect(self._on_apply_analyzed)
        self._worker.row_applied.connect(self._on_apply_applied)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_apply_finished)

        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self._update_action_states()  # 버튼을 Cancel 로
        self.statusBar().showMessage(f"Applying gain to {len(paths)} file(s)...")
        self._worker.start()

    def _on_clear(self):
        """Clear 버튼/단축키: 목록 전체 삭제(원본 ClearAll 대응).

        선택 여부와 무관하게 항상 전부 비운다(원본 lstvMain.ListItems.Clear).
        선택 행만 지우는 것은 Delete 키(_on_delete_selected, 원본 ClearFiles)가
        전담해 역할이 갈린다. 파일 목록만 비울 뿐 파일 자체는 건드리지 않으므로
        확인 대화상자는 두지 않는다(원본도 없음). 워커 실행 중에는 잠근다.
        Clear 후 pending 이 사라지므로 겸용 버튼은 기본(Cancel 비활성)으로 복귀.
        """
        if self._is_busy():
            return
        self.model.clear()

    def _on_delete_selected(self):
        """Delete 키: 선택 행만 삭제(원본 ClearFiles). 선택 없으면 무동작.

        _on_clear 와 달리 선택이 없을 때 전체 삭제하지 않는다(원본 동작).
        분석/적용/스캔 중에는 목록 변경을 잠근다.
        """
        if self._is_busy():
            return
        rows = self._selected_source_rows()
        if rows:
            self.model.remove_rows(rows)

    def _on_double_click(self, index: QModelIndex):
        """더블클릭한 곡을 OS 기본 앱으로 연다(원본 lstvMain_DblClick 대응).

        index 는 프록시(뷰) 좌표이므로 mapToSource 로 원본 행을 구해 path 를
        얻는다. 파일이 없거나 열기 실패 시 상태바로 안내하고 넘어간다.
        """
        if not index.isValid():
            return
        r = self.proxy.mapToSource(index).row()
        fr = self.model.get_row(r)
        if fr is None:
            return
        if not os.path.exists(fr.path):
            self.statusBar().showMessage(f"File not found: {fr.path}")
            return
        try:
            open_with_default_app(fr.path)
        except Exception as exc:
            self.statusBar().showMessage(f"Could not open file: {exc}")

    def _on_target_changed(self, value):
        # 목표가 바뀌면 값이 있는 전 행을 재계산해 다시 표시(원본 targetChange
        # → GainAdjust → DispJunk). 재분석은 하지 않는다(가볍다).
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is None or not fr.result:
                continue
            if fr.result.get("status") != "ok":
                continue
            fr.result = recompute_target(fr.result, value)
            self.model.row_changed(r)
        self.statusBar().showMessage(f"Target set to {value:.1f} dB")

    # --- 태그 스캔 워커 슬롯(전부 메인 스레드: 모델 변경은 여기서만) ---

    def _on_scan_current(self, path: str):
        # 처리 직전: 지금까지 완료 수(오프셋+scanned)와 지금 파일명을 표시.
        done = self._scan_offset + self._scanned_count
        self.statusBar().showMessage(
            f"Scanning tags {done}/{self._scan_total} — {os.path.basename(path)}")

    def _on_scan_progress(self, done: int, total_in_batch: int):
        # done 은 이번 워커 내 카운트. 전체 목록 대비로 보이도록 오프셋을 더한다.
        overall_done = self._scan_offset + done
        self.progress.setValue(overall_done)

    def _on_scan_row_done(self, path: str, result: dict):
        self._scanned_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return  # 그 사이 삭제됨
        fr = self.model.get_row(r)
        fr.set_tag_result(result)  # status "ok"→analyzed / "no_tag"→pending
        self.model.row_changed(r)

    def _on_scan_finished(self):
        # None 처리 전에 중단(Pause) 여부를 읽어둔다.
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self._update_action_states()  # 멈춤 → pending 있으면 Rescan 로
        done = self._scanned_count
        total = self.model.row_count()
        if cancelled:
            # Pause: 진행바를 리셋하지 않고 현재값(스캔된 만큼) 그대로 둔다.
            self.statusBar().showMessage(
                f"Paused — scanned {self._scan_offset + done}/{total} tag(s). "
                f"Press Rescan to continue."
            )
        else:
            # 완료: 100% 를 찍었으면 완료로 판정(리셋하지 않고 꽉 채워 둔다).
            # 이후 파일을 추가하면 분모가 커져 자연히 비율이 줄었다 다시 찬다.
            self.progress.setRange(0, total)
            self.progress.setValue(total)
            self.statusBar().showMessage(
                f"Tag scan done — {total} file(s) total"
            )

    # --- 분석 워커 슬롯 ---

    def _on_analyze_current(self, path: str):
        done = self._analyzed_count
        self.statusBar().showMessage(
            f"Analyzing {done}/{self._batch_total} — {os.path.basename(path)}")

    def _on_worker_progress(self, done: int, total: int):
        self.progress.setValue(done)

    def _on_worker_row_done(self, path: str, result: dict):
        self._analyzed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return  # 그 사이 삭제됨
        fr = self.model.get_row(r)
        fr.set_result(result)
        self.model.row_changed(r)

    def _on_worker_failed(self, path: str, msg: str):
        self._failed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.mark_error(msg)
        self.model.row_changed(r)

    def _on_worker_finished(self):
        # None 처리 전에 취소 여부를 읽어둔다(이후 self._worker 는 사라짐).
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self.progress.setValue(0)
        self._update_action_states()
        done = self._analyzed_count
        failed = self._failed_count
        parts = [f"Analyzed {done} file(s)"]
        if failed:
            parts.append(f"{failed} failed")
        msg = ", ".join(parts)
        self.statusBar().showMessage(f"Cancelled — {msg}" if cancelled else msg)

    # --- 적용 워커 슬롯(Track Gain) ---

    def _on_apply_current(self, path: str):
        done = self._applied_count + self._analyzed_count
        self.statusBar().showMessage(
            f"Applying {done}/{self._batch_total} — {os.path.basename(path)}")

    def _on_apply_progress(self, done: int, total: int):
        self.progress.setValue(done)

    def _on_apply_analyzed(self, path: str, result: dict):
        """스텝이 0이라 적용하지 않고 분석 결과만 반영(원본 "분석까지만")."""
        self._analyzed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.set_result(result)  # status="analyzed": 재분석 대상에서 제외됨
        self.model.row_changed(r)

    def _on_apply_applied(self, path: str, result: dict):
        """실제 게인이 적용된 행. shift 반영된 표시 dict 로 갱신."""
        self._applied_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.mark_applied(result)  # status="applied"
        self.model.row_changed(r)

    def _on_apply_finished(self):
        # None 처리 전에 취소 여부를 읽어둔다(이후 self._worker 는 사라짐).
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self.progress.setValue(0)
        self._update_action_states()
        applied = self._applied_count
        analyzed_only = self._analyzed_count
        failed = self._failed_count
        parts = [f"Applied gain to {applied} file(s)"]
        if analyzed_only:
            parts.append(f"{analyzed_only} already at target")
        if failed:
            parts.append(f"{failed} failed")
        msg = ", ".join(parts)
        self.statusBar().showMessage(f"Cancelled — {msg}" if cancelled else msg)

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
        if self._is_busy():
            event.ignore()
            return
        urls = event.mimeData().urls()
        paths = [u.toLocalFile() for u in urls if u.isLocalFile()]
        if paths:
            self._add_from(paths)
            event.acceptProposedAction()
        else:
            event.ignore()
