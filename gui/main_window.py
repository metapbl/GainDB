r"""gui/main_window.py — 메인 창(8단계: Track + Album, 태그 스캔·분석·게인·팝업).

원본 MP3GainGUI frmMain 의 화면 구성·동작을 관찰해 독립 구현한다(clean-room).
파일/폴더 추가(버튼 + 드래그앤드롭)·Clear·헤더 클릭 자연 정렬·Delete 키 선택
삭제·더블클릭 재생에 더해, 파일 추가 시 태그를 백그라운드 워커로 읽어 표시
(원본 AddSingleFile), Track/Album 의 Analysis 와 Gain 을 QThread 워커로 연결한다.
우클릭 팝업(원본 mnuPopup)으로 Clear Analysis·Undo·Remove Tags·Play 를 제공한다.

메뉴바 + 툴바 공존(원본 frmMain 도 메뉴+툴바 병존). Track 액션의 QAction 을
메뉴에도 재사용해 단축키·enabled 관리를 한 곳으로 통일한다. Album 은 신규
QAction(Album Analysis=Ctrl+U / Album Gain=Ctrl+B / Each folder is album 체크).

Album 배선의 핵심 원칙(지난 실패 예방): Album 워커의 시그널 중 Track 과 의미가
같은 것(current/progress/file_progress/row_done/failed/done)은 검증된 기존
슬롯을 그대로 재사용한다. 이로써 "분석 카운트 0 고정"(row_done 슬롯이 카운트를
올림)과 "진행바 튐"(progress 슬롯이 완료 곡 수 base 를 갱신)이 구조적으로
발생하지 않는다. Album 고유 시그널(row_raw/album_done)만 새 슬롯을 단다.

씨앗 재사용(_album_raws): Album Analysis 로 모은 곡별 원재료(histogram 포함)를
Album Gain 이 재사용해 이중 디코딩을 막는다. 파일 목록이 바뀌면(add/remove/
clear) 앨범 그룹 구성이 달라지므로 _album_raws 를 통째로 비운다(부분 무효화보다
정확 — 앨범 dB 는 그룹 전체에 의존). target(목표 dB) 변경은 raw 의 track_db·
histogram 에 영향이 없어 씨앗을 유지한다(표시만 recompute).

태그 스캔 워커화(대량 추가 프리징 해소): 파일 추가 시 행은 메인에서 즉시 만들고
(빈칸 상태로 목록에 바로 보임), 태그는 TagScanWorker 가 백그라운드로 채운다.
스캔 진행 중에는 겸용 버튼이 Pause 로, 멈춘 뒤 미스캔(pending) 행이 남으면
Rescan 으로 바뀐다(같은 자리에서 상태 전환). 분석/게인/파일 액션 진행 중에는
같은 버튼이 Cancel 이다(작업 성격상 이어가기 개념이 없어 Rescan 없음).

우클릭 팝업(원본 mnuPopup 재현, MVP 범위): Clear Analysis(표시 리셋·파일 미변경,
원본 ResetAnalysis) / Undo Gain changes(파일 변경, UndoFileGain) / Remove Tags
(파일 변경, DeleteFileTags) / Play mp3 file(기본앱 재생). 우클릭한 행이 선택에
없으면 그 행만 선택한 뒤 메뉴를 띄운다(데스크톱 관례 + 원본 "선택 한정" 취지).

취소·진행률: 취소는 청크 경계에서 반영된다(워커가 decode 계층에 취소 콜백을
넘겨 진행 중 ffmpeg 를 즉시 kill). 긴 곡 디코딩 중 파일 내부 진행률(0~1)을
받아 상태바·진행바 세분 합산에 반영한다. undo·태그 제거는 디코딩이 없어 파일
내부 진행률이 없고 취소는 파일 경계다.

진행바 세분 합산: 분석/적용 진행바는 파일 단위가 아니라 파일 내부 진행까지
합산해 부드럽게 흐른다. 정수 진행바에 소수 진행을 싣기 위해 _PROGRESS_SCALE
(=1000)을 곱한 스케일을 쓴다: 값 = (완료 파일수 + 현재 파일 fraction) * 1000.
태그 스캔·파일 액션 진행바는 성격이 달라(내부 진행 없음) 파일 단위 방식이다.

Path\File 컬럼은 PathElideDelegate 로 그린다: 경로를 먼저 접고(C:\...\MUSIC\)
파일명을 최후까지 보존하며, 그래도 좁으면 그때만 파일명을 elide 한다.

겸용 버튼(진행바 옆) 규칙 — _update_action_states 에서 결정:
  - 태그 스캔 워커 실행 중          -> "Pause" (활성)   : 파일 경계에서 스캔 중단
  - 분석/적용/액션 워커 실행 중     -> "Cancel"(활성)   : 청크/파일 경계에서 중단
  - 멈춤 + 미스캔(pending) 행 있음  -> "Rescan"(활성)   : 남은 pending 이어 스캔
  - 멈춤 + pending 없음             -> "Cancel"(비활성) : 동작 없음(기본 상태)

GUI 무계산 원칙: 수치는 gaindb.api 가 계산한 것만 표시한다.
정렬 순서는 프록시(뷰) 좌표, 실제 데이터는 원본 모델 좌표이므로
삭제·더블클릭·워커 결과 반영 시 반드시 좌표를 구분한다.

워커 규칙: 무거운 작업(ffmpeg 디코딩·파일 적용)은 워커에서 돌리고, 워커는
시그널만 방출한다. 모델 변경은 전부 메인 스레드의 슬롯에서 수행한다.
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
    QAbstractItemView, QHeaderView, QRubberBand, QStyledItemDelegate, QMenu,
)

from PySide6.QtGui import QAction, QKeySequence

from gui.model import FileTableModel, SORT_ROLE
from gui.columns import Col
from gui.workers import (
    TagScanWorker, AnalyzeWorker, ApplyWorker, FileActionWorker,
    AlbumAnalyzeWorker, AlbumApplyWorker,
)
from gaindb.api import (
    DEFAULT_TARGET_DB, recompute_target, shift_after_apply, group_by_album,
)

# 진행바 세분 합산 스케일. 정수 진행바에 소수 진행(파일 내부 fraction)을 싣기
# 위한 배율. 1000 이면 0.1% 단위(소수점 한 자리)까지 표현된다.
_PROGRESS_SCALE = 1000


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
    r"""Path\File 컬럼 전용 델리게이트: 경로를 먼저 접고 파일명을 최후까지 보존.

    표준 elide 모드는 문자열을 한 지점에서만 접어 "경로만 접고 파일명은 보존,
    그래도 좁으면 파일명 자름"이라는 2단계 규칙을 표현할 수 없다. 그래서 직접
    그린다. 셀 폭에 맞춰 단계적으로 축소한다:
      1) 전체 경로가 다 들어가면 그대로.
      2) 안 들어가면 경로를 접는다: 드라이브 + \...\ + 마지막 폴더 + \ + 파일명.
      3) 그렇게 최소로 접어도 넘치면 그때만 파일명을 뒤에서 elide 한다.
    그리기만 커스터마이즈하고 배경·선택 하이라이트는 기본 스타일에 맡겨
    다크테마 팔레트를 깨지 않는다. 전체 경로 툴팁·정렬은 모델이 담당한다.
    """

    _SEP = "\u2026"  # '...' (한 글자 말줄임표)

    def _elide_path(self, text: str, avail: int, fm) -> str:
        """text(전체 경로)를 폭 avail(px)에 맞춰 단계적으로 축소한 문자열."""
        if fm.horizontalAdvance(text) <= avail:
            return text

        sep = "\\" if "\\" in text else "/"
        parts = text.split(sep)
        if len(parts) >= 3:
            drive = parts[0]
            filename = parts[-1]
            last_dir = parts[-2]
            folded = f"{drive}{sep}{self._SEP}{sep}{last_dir}{sep}{filename}"
            if fm.horizontalAdvance(folded) <= avail:
                return folded
            prefix = f"{drive}{sep}{self._SEP}{sep}{last_dir}{sep}"
            prefix_w = fm.horizontalAdvance(prefix)
            remain = avail - prefix_w
            if remain <= 0:
                return fm.elidedText(text, Qt.TextElideMode.ElideLeft, avail)
            elided_name = fm.elidedText(
                filename, Qt.TextElideMode.ElideRight, remain)
            return prefix + elided_name

        return fm.elidedText(text, Qt.TextElideMode.ElideLeft, avail)

    def paint(self, painter, option, index):
        from PySide6.QtWidgets import QStyle, QApplication

        text = index.data(Qt.ItemDataRole.DisplayRole) or ""

        opt = self.initStyleOption_copy(option, index)
        opt.text = ""
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
    """Delete 키 삭제 + 빈 영역 고무줄 선택 + 우클릭 팝업을 지원하는 QTableView."""

    delete_requested = Signal()
    context_menu_requested = Signal(QPoint)  # 전역 좌표

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rubber_band: QRubberBand | None = None
        self._rubber_origin = QPoint()
        self._rubber_active = False
        self._rubber_additive = False

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Delete:
            self.delete_requested.emit()
            event.accept()
            return
        if event.key() == Qt.Key.Key_Escape:
            if self.selectionModel() and self.selectionModel().hasSelection():
                self.clearSelection()
                event.accept()
                return
        super().keyPressEvent(event)

    def contextMenuEvent(self, event):
        """우클릭: 그 행이 선택에 없으면 그 행만 선택한 뒤 메뉴 요청을 방출."""
        pos = event.pos()
        index = self.indexAt(pos)
        if index.isValid():
            sel = self.selectionModel()
            if not sel.isRowSelected(index.row(), QModelIndex()):
                self.selectRow(index.row())
        else:
            self.clearSelection()
        self.context_menu_requested.emit(event.globalPos())
        event.accept()

    def mousePressEvent(self, event):
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
        """뷰포트 좌표 사각형 rect 에 걸치는 행을 선택한다."""
        sel_model = self.selectionModel()
        model = self.model()
        if model is None:
            return

        from PySide6.QtCore import QItemSelection, QItemSelectionModel

        selection = QItemSelection()
        last_col = model.columnCount() - 1
        for r in range(model.rowCount()):
            row_rect = self.visualRect(model.index(r, 0))
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
    """Windows 11 탐색기식 자연 정렬 프록시."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setSortRole(SORT_ROLE)
        self._collator = QCollator()
        self._collator.setNumericMode(True)
        self._collator.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)

    def lessThan(self, left: QModelIndex, right: QModelIndex) -> bool:
        lv = self.sourceModel().data(left, SORT_ROLE)
        rv = self.sourceModel().data(right, SORT_ROLE)

        if lv is None and rv is None:
            return False
        descending = self.sortOrder() == Qt.SortOrder.DescendingOrder
        if lv is None:
            return descending
        if rv is None:
            return not descending

        if isinstance(lv, str) or isinstance(rv, str):
            return self._collator.compare(str(lv), str(rv)) < 0
        return lv < rv


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Gain dB")
        self.resize(1040, 560)
        self.setAcceptDrops(True)

        self.model = FileTableModel(self)
        self.proxy = NaturalSortProxy(self)
        self.proxy.setSourceModel(self.model)

        # 실행 중 워커 보유(GC 방지). 한 번에 한 종류만 돈다(busy 잠금).
        # _worker_kind: "scan"|"analyze"|"apply"|"action"|
        #               "album_analyze"|"album_apply"|None.
        self._worker = None
        self._worker_kind: str | None = None
        self._scanned_count = 0
        self._scan_offset = 0
        self._scan_total = 0
        self._analyzed_count = 0
        self._applied_count = 0
        self._failed_count = 0
        self._batch_total = 0
        self._action_done = 0
        self._action_verb = ""
        self._current_name = ""
        self._current_fraction = 0.0
        # 진행바 전용 base(완료 곡 수). file_progress 와 progress 가
        # 같은 base 를 공유해 진행바 튐을 막는다(_analyzed_count 는
        # 성공만 세어 base 로 못 씀 - 실패 곡이 섞이면 엇갈리기 때문).
        self._progress_base = 0
        self._album_applying = False

        # Album 씨앗: {path: analyze_album_file 원재료(histogram 포함)}.
        # Album Analysis 로 채우고 Album Gain 이 재사용해 이중 디코딩을 막는다.
        # 파일 목록 변경 시 통째로 비운다(_invalidate_album_seeds).
        self._album_raws: dict[str, dict] = {}

        self._build_menubar()
        self._build_toolbar()
        self._build_central()
        self._build_statusbar()
        self._build_context_menu()
        self._update_action_states()

    # --- UI 구성 ---

    def _build_menubar(self):
        """메뉴바(원본 frmMain 메뉴 재현). Track 액션은 QAction 을 툴바와 공유.

        Track 액션(act_*)은 _build_toolbar 에서 만든다. 메뉴바를 먼저 만들되
        Track 액션은 _build_toolbar 뒤 _wire_menu_actions 에서 addAction 한다.
        여기서는 메뉴와 Album 신규 액션만 만든다(단축키·enabled 통일).
        """
        mb = self.menuBar()
        self.menu_file = mb.addMenu("File")
        self.menu_analysis = mb.addMenu("Analysis")
        self.menu_modify = mb.addMenu("Modify")
        self.menu_options = mb.addMenu("Options")

        # Album 신규 액션(Track act_* 는 툴바에서 생성 후 공유).
        self.act_album_analyze = QAction("Album Analysis", self)
        self.act_album_analyze.setShortcut(QKeySequence("Ctrl+U"))
        self.act_album_analyze.setToolTip(
            "Analyze album gain per folder/group without applying (Ctrl+U)")
        self.act_album_analyze.triggered.connect(self._on_album_analyze)

        self.act_album_gain = QAction("Album Gain", self)
        self.act_album_gain.setShortcut(QKeySequence("Ctrl+B"))
        self.act_album_gain.setToolTip(
            "Apply album gain to files per folder/group (Ctrl+B)")
        self.act_album_gain.triggered.connect(self._on_album_gain)

        # Clear Analysis(선택 행 표시 리셋) — 팝업 핸들러 재사용.
        self.act_clear_analysis = QAction("Clear Analysis", self)
        self.act_clear_analysis.setToolTip(
            "Clear analysis values of selected files (does not change files)")
        self.act_clear_analysis.triggered.connect(self._on_ctx_clear_analysis)

        # Undo(선택 행 게인 되돌리기) — 팝업 핸들러 재사용.
        self.act_undo = QAction("Undo Gain changes", self)
        self.act_undo.setToolTip("Undo gain changes of selected files")
        self.act_undo.triggered.connect(self._on_ctx_undo)

        # Each folder is album(원본 mnuEachAlbum) — 체크 액션, 기본 켜짐.
        self.act_each_folder_album = QAction("Each folder is album", self)
        self.act_each_folder_album.setCheckable(True)
        self.act_each_folder_album.setChecked(True)
        self.act_each_folder_album.setToolTip(
            "Treat each folder as a separate album (else all files = one album)")

    def _wire_menu_actions(self):
        """툴바 Track 액션이 만들어진 뒤 메뉴에 배치한다(액션 공유)."""
        self.menu_file.addAction(self.act_add_files)
        self.menu_file.addAction(self.act_add_folder)
        self.menu_file.addSeparator()
        self.menu_file.addAction(self.act_clear)

        self.menu_analysis.addAction(self.act_analyze)
        self.menu_analysis.addAction(self.act_album_analyze)
        self.menu_analysis.addSeparator()
        self.menu_analysis.addAction(self.act_clear_analysis)

        self.menu_modify.addAction(self.act_gain)
        self.menu_modify.addAction(self.act_album_gain)
        self.menu_modify.addSeparator()
        self.menu_modify.addAction(self.act_undo)

        self.menu_options.addAction(self.act_each_folder_album)

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

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

        # Album 액션도 툴바에 노출(메뉴와 QAction 공유).
        tb.addAction(self.act_album_analyze)
        tb.addAction(self.act_album_gain)

        tb.addSeparator()

        self.act_clear = QAction("Clear", self)
        self.act_clear.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
        self.act_clear.setToolTip(
            "Clear all files from the list (Ctrl+Shift+Delete)"
        )
        self.act_clear.triggered.connect(self._on_clear)
        tb.addAction(self.act_clear)

        # 툴바 Track 액션이 준비됐으니 메뉴에 배치(액션 공유).
        self._wire_menu_actions()

    def _build_central(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)

        target_row = QHBoxLayout()
        target_row.addWidget(QLabel("Target Volume:"))
        self.spin_target = QDoubleSpinBox(self)
        self.spin_target.setDecimals(1)
        self.spin_target.setSingleStep(1.0)
        self.spin_target.setRange(75.0, 105.0)
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

        self.table = FileTableView(self)
        self.table.setModel(self.proxy)
        self.table.setSortingEnabled(True)
        self.table.setItemDelegateForColumn(
            int(Col.NAME), PathElideDelegate(self.table))
        self.table.verticalHeader().setDefaultSectionSize(22)
        self.table.sortByColumn(int(Col.NAME), Qt.SortOrder.AscendingOrder)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setSelectionMode(
            QAbstractItemView.SelectionMode.ExtendedSelection)
        self.table.setAlternatingRowColors(True)
        self.table.verticalHeader().setVisible(False)
        self.table.delete_requested.connect(self._on_delete_selected)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.context_menu_requested.connect(self._show_context_menu)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(
            int(Col.NAME), QHeaderView.ResizeMode.Stretch)
        # Track + Album 수치 컬럼 전부 내용맞춤(원본 컬럼 순서, columns.py 정의).
        for c in (Col.VOLUME, Col.TRACK_GAIN, Col.CLIP,
                  Col.ALBUM_VOLUME, Col.ALBUM_GAIN, Col.ALBUM_CLIP,
                  Col.MAX_AMP):
            header.setSectionResizeMode(
                int(c), QHeaderView.ResizeMode.ResizeToContents)
        self.model.rowsInserted.connect(self._update_action_states)
        self.model.rowsRemoved.connect(self._update_action_states)
        self.model.modelReset.connect(self._update_action_states)
        layout.addWidget(self.table)

        prog_row = QHBoxLayout()
        prog_row.addWidget(QLabel("Progress:"))
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        prog_row.addWidget(self.progress, 1)
        self.btn_action = QPushButton("Cancel", self)
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self._on_action_button)
        prog_row.addWidget(self.btn_action)
        layout.addLayout(prog_row)

        self.setCentralWidget(central)

    def _build_statusbar(self):
        self.statusBar().showMessage("Ready")

    def _build_context_menu(self):
        """우클릭 팝업(원본 mnuPopup 재현, MVP 항목)을 구성한다."""
        self.ctx_menu = QMenu(self)

        self.ctx_clear_analysis = QAction("Clear Analysis", self)
        self.ctx_clear_analysis.triggered.connect(self._on_ctx_clear_analysis)
        self.ctx_menu.addAction(self.ctx_clear_analysis)

        self.ctx_menu.addSeparator()

        self.ctx_undo = QAction("Undo Gain changes", self)
        self.ctx_undo.triggered.connect(self._on_ctx_undo)
        self.ctx_menu.addAction(self.ctx_undo)

        self.ctx_remove_tags = QAction("Remove Tags from files", self)
        self.ctx_remove_tags.triggered.connect(self._on_ctx_remove_tags)
        self.ctx_menu.addAction(self.ctx_remove_tags)

        self.ctx_menu.addSeparator()

        self.ctx_play = QAction("Play mp3 file", self)
        self.ctx_play.triggered.connect(self._on_ctx_play)
        self.ctx_menu.addAction(self.ctx_play)

    # --- Album 씨앗 관리 ---

    def _invalidate_album_seeds(self):
        """앨범 씨앗을 통째로 비운다(파일 목록이 바뀌어 그룹 구성이 달라질 때).

        앨범 dB 는 그룹 전체 곡의 히스토그램 합에 의존하므로, 목록이 바뀌면
        부분 무효화보다 전체 무효화가 정확하다. target 변경은 raw 에 영향이
        없어 여기서 부르지 않는다(표시만 recompute).
        """
        self._album_raws.clear()

    # --- 진행바 세분 합산 헬퍼 ---

    def _set_batch_progress(self, done: int, fraction: float):
        """분석/적용 진행바를 세분 합산 값으로 설정한다."""
        frac = 0.0 if fraction < 0.0 else (1.0 if fraction > 1.0 else fraction)
        self.progress.setValue(int((done + frac) * _PROGRESS_SCALE))

    def _batch_status(self, verb: str, done: int) -> str:
        """작업 중 상태바 문구: "verb k/N - 파일명 - NN.N%"."""
        msg = f"{verb} {done}/{self._batch_total}"
        if self._current_name:
            msg += f" - {self._current_name}"
            msg += f" - {self._current_fraction * 100.0:.1f}%"
        return msg

    # --- 상태 갱신 ---

    def _is_busy(self) -> bool:
        return self._worker is not None

    def _has_pending(self) -> bool:
        """목록에 태그 스캔 미시도(Rescan 대상) 행이 하나라도 있는지."""
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is not None and fr.needs_tag_scan():
                return True
        return False

    def _update_action_states(self, *args):
        busy = self._is_busy()
        has_rows = self.model.rowCount() > 0
        self.act_add_files.setEnabled(not busy)
        self.act_add_folder.setEnabled(not busy)
        self.act_analyze.setEnabled(has_rows and not busy)
        self.act_gain.setEnabled(has_rows and not busy)
        self.act_album_analyze.setEnabled(has_rows and not busy)
        self.act_album_gain.setEnabled(has_rows and not busy)
        self.act_clear.setEnabled(has_rows and not busy)
        self.act_clear_analysis.setEnabled(has_rows and not busy)
        self.act_undo.setEnabled(has_rows and not busy)

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
        """진행바 옆 겸용 버튼. 현재 상태에 따라 pause/cancel/rescan."""
        if self._is_busy():
            if self._worker is not None:
                self._worker.request_cancel()
                self.btn_action.setEnabled(False)
                if self._worker_kind == "scan":
                    self.statusBar().showMessage("Pausing after current file...")
                else:
                    self.statusBar().showMessage("Cancelling...")
            return
        self._start_tag_scan(self._pending_paths())

    # --- 대상 행 결정 ---

    def _pending_paths(self) -> list[str]:
        """태그 스캔 미시도(Rescan 대상) 행들의 경로."""
        paths = []
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is not None and fr.needs_tag_scan():
                paths.append(fr.path)
        return paths

    def _target_source_rows(self) -> list[int]:
        """작업 대상 모델 행 인덱스. 선택 행이 있으면 그것, 없으면 전체."""
        sel = self.table.selectionModel().selectedRows()
        if sel:
            return [self.proxy.mapToSource(idx).row() for idx in sel]
        return list(range(self.model.row_count()))

    def _selected_source_rows(self) -> list[int]:
        """선택된 행의 원본 모델 인덱스만 반환(선택 없으면 빈 리스트)."""
        sel = self.table.selectionModel().selectedRows()
        return [self.proxy.mapToSource(idx).row() for idx in sel]

    # --- 태그 스캔 워커 시작 ---

    def _start_tag_scan(self, paths: list[str]):
        """주어진 경로들의 태그를 백그라운드로 스캔한다(원본 AddSingleFile)."""
        if self._is_busy() or not paths:
            self._update_action_states()
            return
        target_db = self.spin_target.value()
        total = self.model.row_count()
        self._scan_offset = total - len(paths)
        self._scan_total = total
        self._scanned_count = 0
        self._worker = TagScanWorker(paths, target_db, self)
        self._worker_kind = "scan"
        self._worker.current.connect(self._on_scan_current)
        self._worker.progress.connect(self._on_scan_progress)
        self._worker.row_done.connect(self._on_scan_row_done)
        self._worker.done.connect(self._on_scan_finished)

        self.progress.setRange(0, total)
        self.progress.setValue(self._scan_offset)
        self._update_action_states()
        self.statusBar().showMessage(
            f"Scanning tags {self._scan_offset}/{total}")
        self._worker.start()

    # --- 파일 추가 공통 ---

    def _add_from(self, paths):
        if self._is_busy():
            self.statusBar().showMessage("Busy - wait for the current task")
            return
        mp3s = collect_mp3_paths(paths, recurse=True)
        if not mp3s:
            self.statusBar().showMessage("No .mp3 files found")
            return
        new_rows = self.model.add_paths(mp3s)
        if not new_rows:
            self.statusBar().showMessage(
                f"No new files, {self.model.rowCount()} total"
            )
            return
        # 파일 목록이 바뀌었으니 앨범 씨앗을 통째로 무효화.
        self._invalidate_album_seeds()
        self.statusBar().showMessage(
            f"Added {len(new_rows)} file(s), {self.model.rowCount()} total - "
            f"scanning tags..."
        )
        self._start_tag_scan(self._pending_paths())

    # --- 툴바/메뉴 액션 ---

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
        self._current_name = ""
        self._current_fraction = 0.0
        self._progress_base = 0
        self._album_applying = False
        self._worker = AnalyzeWorker(paths, target_db, self)
        self._worker_kind = "analyze"
        self._worker.current.connect(self._on_analyze_current)
        self._worker.file_progress.connect(self._on_analyze_file_progress)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.row_done.connect(self._on_worker_row_done)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_worker_finished)

        self.progress.setRange(0, len(paths) * _PROGRESS_SCALE)
        self.progress.setValue(0)
        self._update_action_states()
        self.statusBar().showMessage(f"Analyzing {len(paths)} file(s)...")
        self._worker.start()

    def _on_gain(self):
        """Track Gain 적용(원본 RadioGain 재현). ApplyWorker 로 위임한다."""
        if self._is_busy():
            return

        rows = self._target_source_rows()
        self._dlog("TRACK_GAIN_CLICK rows=" + str(len(rows)) + " total_rows=" + str(self.model.row_count()))  # DEBUGLOG
        paths = []
        seed_results = {}
        for r in rows:
            fr = self.model.get_row(r)
            if fr is None:
                self._dlog("TRACK_GAIN row " + str(r) + " -> None (SKIPPED)")  # DEBUGLOG
                continue
            paths.append(fr.path)
            seed_results[fr.path] = fr.result
        self._dlog("TRACK_GAIN paths=" + str(len(paths)))  # DEBUGLOG

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
        self._current_name = ""
        self._current_fraction = 0.0
        self._progress_base = 0
        self._album_applying = False
        self._worker = ApplyWorker(paths, target_db, seed_results, self)
        self._worker_kind = "apply"
        self._worker.current.connect(self._on_apply_current)
        self._worker.file_progress.connect(self._on_apply_file_progress)
        self._worker.progress.connect(self._on_apply_progress)
        self._worker.row_analyzed.connect(self._on_apply_analyzed)
        self._worker.row_applied.connect(self._on_apply_applied)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_apply_finished)

        self.progress.setRange(0, len(paths) * _PROGRESS_SCALE)
        self.progress.setValue(0)
        self._update_action_states()
        self.statusBar().showMessage(f"Applying gain to {len(paths)} file(s)...")
        self._worker.start()

    # --- Album Analysis / Album Gain 핸들러 ---

    def _dlog(self, msg):  # DEBUGLOG
        try:
            open("debug.log","a",encoding="utf-8").write(msg + "\n")
        except Exception:
            pass

    def _on_album_analyze(self):
        """Album Analysis(원본 album 모드 재현). 선택(없으면 전체) 전부 분석.

        원본 mp3gain -a 는 지정 파일 전부를 분석해 그룹 히스토그램을 합산한다.
        일부만 분석하면 앨범 dB 가 틀리므로 needs_analysis 필터를 걸지 않는다
        (Track 값이 있어도 Album 값은 없을 수 있어 재분석이 옳다). 진행/카운트
        슬롯은 Track 분석과 동일한 것을 재사용하고, 앨범 고유 시그널만 새 슬롯.
        """
        self._dlog("ALBUM_ANALYZE_CLICK busy=" + str(self._is_busy()))  # DEBUGLOG
        if self._is_busy():
            return

        rows = self._target_source_rows()
        paths = []
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                paths.append(fr.path)
        self._dlog("ALBUM_ANALYZE rows=" + str(len(rows)) + " paths=" + str(len(paths)))  # DEBUGLOG

        if not paths:
            self.statusBar().showMessage("No files to analyze")
            return

        each_folder = self.act_each_folder_album.isChecked()
        groups = group_by_album(paths, each_folder_is_album=each_folder)

        target_db = self.spin_target.value()
        self._analyzed_count = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._current_name = ""
        self._current_fraction = 0.0
        self._progress_base = 0
        self._album_applying = False
        self._worker = AlbumAnalyzeWorker(groups, target_db, self)
        self._worker_kind = "album_analyze"
        self._worker.current.connect(self._on_analyze_current)
        self._worker.file_progress.connect(self._on_analyze_file_progress)
        self._worker.progress.connect(self._on_worker_progress)
        self._worker.row_done.connect(self._on_worker_row_done)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_worker_finished)
        self._worker.row_raw.connect(self._on_album_row_raw)
        self._worker.album_done.connect(self._on_album_group_done)

        self.progress.setRange(0, len(paths) * _PROGRESS_SCALE)
        self.progress.setValue(0)
        self._update_action_states()
        self._dlog("ALBUM_ANALYZE_START groups=" + str(len(groups)))  # DEBUGLOG
        self.statusBar().showMessage(
            "Analyzing " + str(len(paths)) + " file(s) in "
            + str(len(groups)) + " album(s)...")
        self._worker.start()


    def _on_album_gain(self):
        """Album Gain 적용(원본 AlbumGain 재현). AlbumApplyWorker 위임.

        대상: 선택 있으면 선택·없으면 전체. 그룹핑은 Each folder is album 체크.
        씨앗(_album_raws)에서 대상 경로 원재료만 추려 넘겨 재디코딩을 막는다
        (없으면 워커가 그 그룹을 분석). 진행/적용 슬롯은 Track Gain 과 동일한
        것을 재사용한다.
        """
        if self._is_busy():
            return

        rows = self._target_source_rows()
        self._dlog("ALBUM_GAIN_CLICK rows=" + str(len(rows)) + " total_rows=" + str(self.model.row_count()))  # DEBUGLOG
        paths = []
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                paths.append(fr.path)
        self._dlog("ALBUM_GAIN paths=" + str(len(paths)))  # DEBUGLOG

        if not paths:
            self.statusBar().showMessage("No files to apply")
            return

        each_folder = self.act_each_folder_album.isChecked()
        groups = group_by_album(paths, each_folder_is_album=each_folder)
        # 대상 경로에 해당하는 씨앗만 추려 넘긴다(나머지는 워커가 분석).
        seed_raws = {p: self._album_raws[p]
                     for p in paths if p in self._album_raws}
        self._dlog("ALBUM_GAIN seeds=" + str(len(seed_raws)) + " groups=" + str(len(groups)))  # DEBUGLOG

        target_db = self.spin_target.value()
        self._analyzed_count = 0
        self._applied_count = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._current_name = ""
        self._current_fraction = 0.0
        self._progress_base = 0
        self._album_applying = False
        self._worker = AlbumApplyWorker(groups, target_db, seed_raws, self)
        self._worker_kind = "album_apply"
        # Track Gain 과 의미가 같은 시그널은 기존 슬롯 재사용.
        self._worker.current.connect(self._on_apply_current)
        self._worker.file_progress.connect(self._on_apply_file_progress)
        self._worker.progress.connect(self._on_apply_progress)
        self._worker.apply_progress.connect(self._on_album_apply_count)
        self._worker.row_analyzed.connect(self._on_apply_analyzed)
        self._worker.row_applied.connect(self._on_apply_applied)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_apply_finished)

        self.progress.setRange(0, len(paths) * _PROGRESS_SCALE)
        self.progress.setValue(0)
        self._update_action_states()
        self.statusBar().showMessage(
            f"Applying album gain to {len(paths)} file(s) in "
            f"{len(groups)} album(s)...")
        self._worker.start()

    def _on_clear(self):
        """Clear 버튼/단축키: 목록 전체 삭제(원본 ClearAll 대응)."""
        if self._is_busy():
            return
        self.model.clear()
        self._invalidate_album_seeds()

    def _on_delete_selected(self):
        """Delete 키: 선택 행만 삭제(원본 ClearFiles). 선택 없으면 무동작."""
        if self._is_busy():
            return
        rows = self._selected_source_rows()
        if rows:
            self.model.remove_rows(rows)
            self._invalidate_album_seeds()

    def _on_double_click(self, index: QModelIndex):
        """더블클릭한 곡을 OS 기본 앱으로 연다(원본 lstvMain_DblClick 대응)."""
        if not index.isValid():
            return
        r = self.proxy.mapToSource(index).row()
        self._play_row(r)

    def _play_row(self, r: int):
        """모델 행 r 의 파일을 기본 앱으로 연다(더블클릭·팝업 Play 공용)."""
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
        # 목표가 바뀌면 값이 있는 전 행을 재계산해 다시 표시(재분석 없음).
        # 씨앗(_album_raws)은 target 에 무관하므로 무효화하지 않는다.
        for r in range(self.model.row_count()):
            fr = self.model.get_row(r)
            if fr is None or not fr.result:
                continue
            if fr.result.get("status") != "ok":
                continue
            fr.result = recompute_target(fr.result, value)
            self.model.row_changed(r)
        self.statusBar().showMessage(f"Target set to {value:.1f} dB")

    # --- 우클릭 팝업 표시 + 항목 핸들러 ---

    def _show_context_menu(self, global_pos):
        """우클릭 팝업을 선택·busy 상태에 맞춰 활성화한 뒤 표시(원본 mnuPopup)."""
        has_sel = len(self.table.selectionModel().selectedRows()) > 0
        busy = self._is_busy()
        enable = has_sel and not busy
        self.ctx_clear_analysis.setEnabled(enable)
        self.ctx_undo.setEnabled(enable)
        self.ctx_remove_tags.setEnabled(enable)
        self.ctx_play.setEnabled(enable)
        self.ctx_menu.exec(global_pos)

    def _on_ctx_clear_analysis(self):
        """선택 행의 표시값만 리셋(파일 미변경, 원본 ResetAnalysis)."""
        if self._is_busy():
            return
        rows = self._selected_source_rows()
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                fr.clear_result()
                self.model.row_changed(r)
        # 이 행들의 씨앗은 이제 표시와 어긋나므로 통째로 무효화(단순·안전).
        if rows:
            self._invalidate_album_seeds()
        self._update_action_states()
        if rows:
            self.statusBar().showMessage(
                f"Cleared analysis of {len(rows)} file(s)")

    def _on_ctx_undo(self):
        """선택 행의 게인 변경을 undo(파일 변경, 원본 UndoFileGain)."""
        self._start_file_action("undo")

    def _on_ctx_remove_tags(self):
        """선택 행의 mp3gain 태그 제거(파일 변경, 원본 DeleteFileTags)."""
        self._start_file_action("remove_tags")

    def _on_ctx_play(self):
        """선택 행(들)을 기본 앱으로 연다(원본 mnuPopupPlayFile)."""
        for r in self._selected_source_rows():
            self._play_row(r)

    # --- 파일 액션 워커(undo / remove_tags) 시작 ---

    def _start_file_action(self, action: str):
        """선택 행에 대해 FileActionWorker(undo|remove_tags)를 돌린다."""
        if self._is_busy():
            return
        rows = self._selected_source_rows()
        paths = []
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                paths.append(fr.path)
        if not paths:
            self.statusBar().showMessage("No files selected")
            return

        self._action_done = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._action_verb = "Undoing" if action == "undo" else "Removing tags"
        self._worker = FileActionWorker(paths, action, use_id3=False, parent=self)
        self._worker_kind = "action"
        self._worker.current.connect(self._on_action_current)
        self._worker.progress.connect(self._on_action_progress)
        self._worker.row_undone.connect(self._on_action_undone)
        self._worker.row_tags_removed.connect(self._on_action_tags_removed)
        self._worker.failed.connect(self._on_worker_failed)
        self._worker.done.connect(self._on_file_action_finished)

        self.progress.setRange(0, len(paths))
        self.progress.setValue(0)
        self._update_action_states()
        self.statusBar().showMessage(f"{self._action_verb} {len(paths)} file(s)...")
        self._worker.start()

    # --- 태그 스캔 워커 슬롯 ---

    def _on_scan_current(self, path: str):
        done = self._scan_offset + self._scanned_count
        self.statusBar().showMessage(
            f"Scanning tags {done}/{self._scan_total} - {os.path.basename(path)}")

    def _on_scan_progress(self, done: int, total_in_batch: int):
        self._scanned_count = done
        overall_done = self._scan_offset + done
        self.progress.setValue(overall_done)

    def _on_scan_row_done(self, path: str, result: dict):
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.set_tag_result(result)
        self.model.row_changed(r)

    def _on_scan_finished(self):
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self._update_action_states()
        done = self._scanned_count
        total = self.model.row_count()
        if cancelled:
            self.statusBar().showMessage(
                f"Paused - scanned {self._scan_offset + done}/{total} tag(s). "
                f"Press Rescan to continue."
            )
        else:
            self.progress.setRange(0, total)
            self.progress.setValue(total)
            self.statusBar().showMessage(
                f"Tag scan done - {total} file(s) total"
            )

    # --- 분석 워커 슬롯(Track Analysis + Album Analysis 공유) ---

    def _on_analyze_current(self, path: str):
        self._current_name = os.path.basename(path)
        self._current_fraction = 0.0
        self.statusBar().showMessage(
            self._batch_status("Analyzing", self._progress_base + 1))

    def _on_analyze_file_progress(self, fraction: float):
        self._current_fraction = fraction
        self._set_batch_progress(self._progress_base, fraction)
        self.statusBar().showMessage(
            self._batch_status("Analyzing", self._progress_base + 1))

    def _on_worker_progress(self, done: int, total: int):
        # 파일 하나 완료: 완료 곡 수(done)를 진행바 base 로 반영하고 내부 진행
        # 리셋. file_progress 와 이 슬롯이 같은 _progress_base 를 공유하므로
        # 진행바가 튀지 않는다(0<->실제값 왕복 해소).
        self._progress_base = done
        self._current_fraction = 0.0
        self._set_batch_progress(done, 0.0)

    def _on_worker_row_done(self, path: str, result: dict):
        # (이 슬롯이 카운트를 올림 -> Album 분석 카운트 0 고정 방지의 핵심.)
        self._analyzed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
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
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self.progress.setValue(0)
        self._current_name = ""
        self._current_fraction = 0.0
        self._update_action_states()
        done = self._analyzed_count
        failed = self._failed_count
        parts = [f"Analyzed {done} file(s)"]
        if failed:
            parts.append(f"{failed} failed")
        msg = ", ".join(parts)
        self.statusBar().showMessage(f"Cancelled - {msg}" if cancelled else msg)

    # --- 앨범 고유 슬롯 ---

    def _on_album_row_raw(self, path: str, raw: dict):
        """앨범 곡 원재료를 씨앗으로 보관(Album Gain 재사용용). 모델 미변경."""
        self._album_raws[path] = raw

    def _on_album_group_done(self, key: str, agg: dict):
        """한 앨범 그룹의 집계 완료(상태바 표기용, 모델 반영은 row_done 이 담당)."""
        # 표시는 row_done(_on_worker_row_done)이 곡별로 처리하므로 여기서는
        # 별도 모델 변경이 없다. 진단·정보 표기 용도로만 남겨둔다.
        pass

    # --- 적용 워커 슬롯(Track Gain + Album Gain 공유) ---

    def _on_apply_current(self, path: str):
        self._current_name = os.path.basename(path)
        self._current_fraction = 0.0
        if self._album_applying:
            return
        _label = "Analyzing" if isinstance(self._worker, AlbumApplyWorker) else "Applying"
        self.statusBar().showMessage(
            self._batch_status(_label, self._progress_base + 1))

    def _on_apply_file_progress(self, fraction: float):
        self._current_fraction = fraction
        self._set_batch_progress(self._progress_base, fraction)
        if self._album_applying:
            return
        _label = "Analyzing" if isinstance(self._worker, AlbumApplyWorker) else "Applying"
        self.statusBar().showMessage(
            self._batch_status(_label, self._progress_base + 1))

    def _on_apply_progress(self, done: int, total: int):
        self._progress_base = done
        self._current_fraction = 0.0
        self._set_batch_progress(done, 0.0)

    def _on_album_apply_count(self, done: int, total: int):
        # 앨범 게인 "적용" 구간 전용: 진행바는 분석에서 이미 100% 도달했으므로
        # 건드리지 않고, 상태바 카운트만 1..N 으로 다시 센다(2안). 이 슬롯이
        # 처음 오면 적용 구간 진입 -> _on_apply_current 가 상태바를 양보한다.
        self._album_applying = True
        self.statusBar().showMessage(
            self._batch_status("Applying", done))

    def _on_apply_analyzed(self, path: str, result: dict):
        """스텝이 0이라 적용하지 않고 분석 결과만 반영."""
        self._analyzed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.set_result(result)
        self.model.row_changed(r)

    def _on_apply_applied(self, path: str, result: dict):
        """실제 게인이 적용된 행. shift 반영된 표시 dict 로 갱신."""
        self._applied_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.mark_applied(result)
        self.model.row_changed(r)

    def _on_apply_finished(self):
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self.progress.setValue(0)
        self._current_name = ""
        self._current_fraction = 0.0
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
        self.statusBar().showMessage(f"Cancelled - {msg}" if cancelled else msg)

    # --- 파일 액션 워커 슬롯(undo / remove_tags) ---

    def _on_action_current(self, path: str):
        self.statusBar().showMessage(
            f"{self._action_verb} {self._action_done}/{self._batch_total} - "
            f"{os.path.basename(path)}")

    def _on_action_progress(self, done: int, total: int):
        self.progress.setValue(done)

    def _on_action_undone(self, path: str, undo_steps: int):
        """undo 성공: 되돌린 스텝으로 표시를 갱신(원본 UndoFileGain 의 AlterDb)."""
        self._action_done += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        if fr.result and fr.result.get("status") == "ok" \
                and fr.result.get("track_db") is not None:
            fr.result = shift_after_apply(fr.result, undo_steps)
            self.model.row_changed(r)

    def _on_action_tags_removed(self, path: str):
        """태그 제거 성공: 행 result 를 비워 미분석(빈칸) 복귀."""
        self._action_done += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.clear_result()
        self.model.row_changed(r)

    def _on_file_action_finished(self):
        cancelled = self._worker.was_cancelled if self._worker else False
        self._worker = None
        self._worker_kind = None
        self.progress.setValue(0)
        # 태그 제거로 표시가 바뀌었을 수 있어 앨범 씨앗을 무효화.
        self._invalidate_album_seeds()
        self._update_action_states()
        done = self._action_done
        failed = self._failed_count
        verb_done = "Undone" if self._action_verb == "Undoing" else "Removed tags from"
        parts = [f"{verb_done} {done} file(s)"]
        if failed:
            parts.append(f"{failed} failed")
        msg = ", ".join(parts)
        self.statusBar().showMessage(f"Cancelled - {msg}" if cancelled else msg)

    # --- 드래그 앤 드롭 ---

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

    # --- 창 닫기: 실행 중 워커 안전 종료 ---

    def closeEvent(self, event):
        """창을 닫을 때 실행 중인 워커를 취소·대기시킨 뒤 닫는다."""
        w = self._worker
        if w is not None:
            w.request_cancel()
            if not w.wait(10000):
                w.terminate()
                w.wait()
        super().closeEvent(event)



