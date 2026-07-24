# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
r"""gui/main_window.py — 메인 창(8단계: Track + Album, 태그 스캔·분석·게인·팝업).

메인 창의 화면 구성·동작을 관찰해 독립 구현한다. 파일/폴더 추가(버튼 +
드래그앤드롭)·Clear·헤더 클릭 자연 정렬·Delete 키 선택 삭제·더블클릭 재생에
더해, 파일 추가 시 태그를 백그라운드 워커로 읽어 표시하고, Track/Album 의
Analysis 와 Gain 을 QThread 워커로 연결한다. 우클릭 팝업으로 Clear Analysis·
Undo·Remove Tags·Play 를 제공한다.

다국어(한글/영문): Language 메뉴로 English/한국어를 고른다(QActionGroup
상호배타). 선택 시 gui.i18n.save_language 로 영속화하고 install_translator 로
즉시 전환한다(Qt 가 LanguageChange 이벤트를 흘리면 changeEvent 가
_retranslate_ui 를 불러 정적 UI 문자열을 다시 tr() 한다). 화면 문자열만 tr()
대상이고, 로그 파일·에러 메시지는 영문 고정이다(합의) — 로그는 사람이 나중에
검색·공유하는 기록이라 CLI 영문 정책과 일관시킨다. 동적 상태바 문구
(_batch_status 등)는 동사/명사 단위만 tr() 로 감싸고 숫자 조립은 f-string 을
유지한다(작업 중 언어 변경은 드물고, 다음 갱신 때 새 언어로 나오므로 실용적
균형 — 정적 UI 는 완전 즉시 전환).

로그: Options → Logs... 로 Error/Analysis/Change 로그 경로·on/off 를 설정한다
(gui/logging.py + gui/dialogs/logs_dialog.py). 각 워커 완료 슬롯에서 이미
보유한 결과 객체를 그대로 포맷해 파일에 append 한다(코어 직접 결과라 stdout
파싱이 필요 없어 단순하다). 로그 실패는 _safe_log 가 잡아 상태바로만 안내하고
본작업을 막지 않는다.

트레이: Options → "Minimize to tray" 체크 시, 창을 최소화하면 창을 숨기고
시스템 트레이 아이콘을 띄운다(changeEvent 로 WindowMinimized 감지). 트레이
아이콘 좌클릭/더블클릭은 창 복원, 우클릭은 팝업(Restore/Exit)이다. X(닫기)는
실제 종료다(트레이로 보내지 않음). macOS 는 창을 Dock 으로 최소화하는 OS
관례가 있어 "자동 최소화→트레이"만 비활성하고 트레이 아이콘·메뉴 자체는
동작한다(플랫폼 가드). 옵션 상태는 QSettings 에 tray/minimize_to_tray 로
영속화한다(로그 설정과 같은 매체).

메뉴바 + 툴바 공존. Track 액션의 QAction 을 메뉴에도 재사용해 단축키·enabled
관리를 한 곳으로 통일한다. Album 은 신규 QAction(Album Analysis=Ctrl+U /
Album Gain=Ctrl+B / Each folder is album 체크).

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

우클릭 팝업(MVP 범위): Clear Analysis(표시 리셋·파일 미변경) / Undo Gain
Changes(파일 변경) / Remove Tags(파일 변경) / Play MP3 file(기본앱 재생).
우클릭한 행이 선택에 없으면 그 행만 선택한 뒤 메뉴를 띄운다(데스크톱 관례 +
"선택 한정" 취지).

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

컬럼폭·정렬·창 기하 영속화(QSettings("GaindB","GaindB")): 창을 닫을 때 저장하고
시작 시 복원한다. 저장 매체(QSettings)·키 문자열은 우리 독립 결정이고, "재기동
시 폭·창 크기·정렬 복원" 동작만 재현한다. 로그 설정(logs/*)·트레이 설정
(tray/*)·언어(i18n/*)도 같은 QSettings 에 함께 영속화한다.
컬럼 폭은 전 컬럼 Interactive(사용자 드래그로 개별 조절, 창 밖으로 넘치면
가로 스크롤 — 창 크기와 독립)로 두고, "Reset Column Widths" 는 columns.py 의
default_width 로 되돌린다. 정렬 상태 저장은 확장 기능이다.

선택 하이라이트 이어짐(완전 매끈): 스타일시트로 셀 테두리와 헤더 섹션 구분선을
없애고, 선택 시 행 전체에 팔레트 Highlight 색을 균일하게 깔아 컬럼 경계에서
선택색이 갈라지지 않게 한다(FullRowSelect 동작에 부합). 다크테마 팔레트 색을
그대로 쓰므로 팔레트 위임 원칙을 깨지 않는다.

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
    QSettings, QByteArray, QEvent,
)
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QDoubleSpinBox,
    QTableView, QToolBar, QProgressBar, QPushButton, QFileDialog,
    QAbstractItemView, QHeaderView, QRubberBand, QStyledItemDelegate, QMenu,
    QSystemTrayIcon, QStyle, QApplication,
)

from PySide6.QtGui import QAction, QActionGroup, QKeySequence

from gui.model import FileTableModel, SORT_ROLE
from gui.columns import Col, COLUMNS, COLUMN_COUNT
from gui.workers import (
    TagScanWorker, AnalyzeWorker, ApplyWorker, FileActionWorker,
    AlbumAnalyzeWorker, AlbumApplyWorker,
)
from gui.logging import (
    LogConfig, LogWriteError,
    log_error, log_analysis_track, log_analysis_album, log_change,
)
from gui.dialogs.logs_dialog import LogsDialog
from gui.dialogs.about_dialog import AboutDialog
from gui.resources import app_icon
from gui.i18n import resolve_language, save_language, install_translator
from gaindb.api import (
    DEFAULT_TARGET_DB, recompute_target, shift_after_apply, group_by_album,
)

# 진행바 세분 합산 스케일. 정수 진행바에 소수 진행(파일 내부 fraction)을 싣기
# 위한 배율. 1000 이면 0.1% 단위(소수점 한 자리)까지 표현된다.
_PROGRESS_SCALE = 1000

# QSettings 조직/앱 이름(크로스플랫폼: Win=레지스트리, macOS=plist).
_SETTINGS_ORG = "GaindB"
_SETTINGS_APP = "GaindB"

# 리스트뷰 스타일시트: 셀 테두리·헤더 섹션 구분선을 없애 선택 하이라이트가
# 컬럼 경계에서 갈라지지 않고 행 전체로 이어지게 한다(완전 매끈). 선택 배경은
# 팔레트 Highlight 색을 그대로 써 다크테마 팔레트 위임을 깨지 않는다.
_TABLE_QSS = """
QTableView {
    border: none;
    gridline-color: transparent;
    outline: none;
}
QTableView::item {
    border: 0px;
    padding: 0px 2px;
}
QTableView::item:selected {
    background: palette(highlight);
    color: palette(highlighted-text);
}
QHeaderView::section {
    border: none;
    border-right: 1px solid palette(mid);
    border-bottom: 1px solid palette(mid);
    padding: 2px 4px;
}
"""

def collect_mp3_paths(paths, recurse: bool = True) -> list[str]:
    """파일/폴더 경로 목록에서 .mp3 파일 경로를 모아 돌려준다.

    - 파일이면 확장자가 .mp3 일 때만 포함.
    - 폴더면 그 안의 .mp3 를 모으고, recurse 면 하위 폴더까지 훑는다
      (하위 폴더 포함 기본 켜짐 동작).
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
    """OS 기본 앱으로 파일을 연다(더블클릭·팝업 Play 의 파일 열기 동작).

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
    배경·선택 하이라이트는 기본 스타일(drawControl)에 맡겨 스타일시트가 지정한
    선택색·매끈한 경계를 그대로 따른다. 전체 경로 툴팁·정렬은 모델이 담당한다.
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
        """option 을 복사·초기화해 반환(원래 option 을 변형하지 않기 위해)."""
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

        self._settings = QSettings(_SETTINGS_ORG, _SETTINGS_APP)
        self._log_config = LogConfig()
        self._load_log_config()
        # 현재 언어(gui.i18n.resolve_language 로 결정. 진입점에서 이미 translator
        # 를 설치했으므로 여기선 메뉴 체크 표시·재선택 판정에만 쓴다).
        self._current_language = resolve_language()
        # 트레이: 지연 생성(트레이 아이콘은 최소화 시 처음 필요). _tray 는
        # QSystemTrayIcon 또는 None. _minimize_to_tray 는 옵션 상태(기본 꺼짐).
        self._tray: QSystemTrayIcon | None = None
        self._minimize_to_tray = False
        self._load_tray_config()

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
        self._build_language_menu()
        self._build_central()
        self._build_statusbar()
        self._build_context_menu()
        self._build_tray()
        self._restore_settings()
        self._update_action_states()

    # --- UI 구성 ---

    def _build_menubar(self):
        """메뉴바를 구성한다. Track 액션은 QAction 을 툴바와 공유.

        Track 액션(act_*)은 _build_toolbar 에서 만든다. 메뉴바를 먼저 만들되
        Track 액션은 _build_toolbar 뒤 _wire_menu_actions 에서 addAction 한다.
        여기서는 메뉴와 Album 신규 액션만 만든다(단축키·enabled 통일).
        """
        mb = self.menuBar()
        self.menu_file = mb.addMenu(self.tr("File"))
        self.menu_analysis = mb.addMenu(self.tr("Analysis"))
        self.menu_modify = mb.addMenu(self.tr("Modify"))
        self.menu_options = mb.addMenu(self.tr("Options"))
        # Language 메뉴는 _build_language_menu 에서 마지막에 추가(오른쪽 끝).

        # Album 신규 액션(Track act_* 는 툴바에서 생성 후 공유).
        self.act_album_analyze = QAction(self.tr("Album Analysis"), self)
        self.act_album_analyze.setShortcut(QKeySequence("Ctrl+U"))
        self.act_album_analyze.setToolTip(self.tr(
            "Analyze album gain per folder/group without applying (Ctrl+U)"))
        self.act_album_analyze.triggered.connect(self._on_album_analyze)

        self.act_album_gain = QAction(self.tr("Album Gain"), self)
        self.act_album_gain.setShortcut(QKeySequence("Ctrl+B"))
        self.act_album_gain.setToolTip(self.tr(
            "Apply album gain to files per folder/group (Ctrl+B)"))
        self.act_album_gain.triggered.connect(self._on_album_gain)

        # Clear Analysis(선택 행 표시 리셋) — 팝업 핸들러 재사용.
        self.act_clear_analysis = QAction(self.tr("Clear Analysis"), self)
        self.act_clear_analysis.setToolTip(self.tr(
            "Clear analysis values of selected files (does not change files)"))
        self.act_clear_analysis.triggered.connect(self._on_ctx_clear_analysis)

        # Undo(선택 행 게인 되돌리기) — 팝업 핸들러 재사용.
        self.act_undo = QAction(self.tr("Undo Gain Changes"), self)
        self.act_undo.setToolTip(self.tr("Undo gain changes of selected files"))
        self.act_undo.triggered.connect(self._on_ctx_undo)

        # Each folder is album — 체크 액션, 기본 켜짐.
        self.act_each_folder_album = QAction(self.tr("Each folder is album"), self)
        self.act_each_folder_album.setCheckable(True)
        self.act_each_folder_album.setChecked(True)
        self.act_each_folder_album.setToolTip(self.tr(
            "Treat each folder as a separate album (else all files = one album)"))

        # Minimize to tray — 체크 액션, 기본 꺼짐.
        self.act_minimize_to_tray = QAction(self.tr("Minimize to tray"), self)
        self.act_minimize_to_tray.setCheckable(True)
        self.act_minimize_to_tray.setChecked(self._minimize_to_tray)
        self.act_minimize_to_tray.setToolTip(self.tr(
            "When minimized, hide the window and show a system tray icon"))
        self.act_minimize_to_tray.toggled.connect(self._on_toggle_tray_option)

        # Logs... — 로그 설정 다이얼로그 열기.
        self.act_logs = QAction(self.tr("Logs..."), self)
        self.act_logs.setToolTip(self.tr(
            "Configure error / analysis / change log files"))
        self.act_logs.triggered.connect(self._on_open_logs)

        # Reset Column Widths — 기본폭으로 되돌림.
        self.act_reset_columns = QAction(self.tr("Reset Column Widths"), self)
        self.act_reset_columns.setToolTip(self.tr(
            "Reset all column widths to their defaults"))
        self.act_reset_columns.triggered.connect(self._reset_column_widths)

        # About — 프로그램 정보·라이선스·서드파티 고지 다이얼로그.
        self.act_about = QAction(
            self.tr("About %1").replace("%1", "Gain dB"), self)
        self.act_about.setToolTip(self.tr(
            "Show program information and license notices"))
        self.act_about.triggered.connect(self._on_about)

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
        self.menu_options.addAction(self.act_minimize_to_tray)
        self.menu_options.addSeparator()
        self.menu_options.addAction(self.act_logs)
        self.menu_options.addAction(self.act_reset_columns)

    def _build_language_menu(self):
        """Language 메뉴를 구성하고, 그 뒤에 Help 메뉴를 맨 오른쪽에 둔다.

        English/한국어를 QActionGroup 으로 상호배타 체크한다. 현재 언어에 체크를
        표시하고, 다른 언어를 고르면 _on_language_selected 가 저장+즉시 전환한다.
        언어 표기 자체는 각 언어의 자기 이름(English / 한국어)이라 tr() 대상이
        아니다(어느 언어로 보든 자기 이름은 동일하게 보이는 게 관례).
        Help 메뉴는 관례상 맨 오른쪽이므로 Language 다음에 추가한다.
        """
        mb = self.menuBar()
        self.menu_language = mb.addMenu(self.tr("Language"))

        self._lang_group = QActionGroup(self)
        self._lang_group.setExclusive(True)

        self.act_lang_en = QAction("English", self)
        self.act_lang_en.setCheckable(True)
        self.act_lang_en.setData("en")
        self._lang_group.addAction(self.act_lang_en)
        self.menu_language.addAction(self.act_lang_en)

        self.act_lang_ko = QAction("한국어", self)
        self.act_lang_ko.setCheckable(True)
        self.act_lang_ko.setData("ko")
        self._lang_group.addAction(self.act_lang_ko)
        self.menu_language.addAction(self.act_lang_ko)

        # 현재 언어에 체크 표시.
        if self._current_language == "ko":
            self.act_lang_ko.setChecked(True)
        else:
            self.act_lang_en.setChecked(True)

        self._lang_group.triggered.connect(self._on_language_selected)

        # Help 메뉴(맨 오른쪽): About 액션은 _build_menubar 에서 생성됨.
        self.menu_help = mb.addMenu(self.tr("Help"))
        self.menu_help.addAction(self.act_about)

    def _on_language_selected(self, action: QAction):
        """언어 메뉴 선택: 같은 언어면 무시, 아니면 저장 + 즉시 전환."""
        lang = action.data()
        if lang == self._current_language:
            return
        self._current_language = lang
        save_language(lang)
        app = QApplication.instance()
        if app is not None:
            install_translator(app, lang)
        # install_translator 성공 시 Qt 가 LanguageChange 이벤트를 흘려
        # changeEvent -> _retranslate_ui 가 호출된다. 만약 이벤트가 안 오면
        # (드묾) 명시적으로 한 번 더 부른다(안전망).
        self._retranslate_ui()

    def _retranslate_ui(self):
        """정적 UI 문자열을 현재 언어로 다시 세팅한다(즉시 전환 시 호출).

        메뉴 제목·액션 캡션/툴팁·툴바·트레이 메뉴·target 라벨·컨텍스트 메뉴·
        진행 버튼 기본 텍스트를 다시 tr() 한다. 컬럼 헤더는 model.headerData 가
        tr() 하므로 헤더만 갱신 신호를 보낸다. 동적 상태바 문구는 다음 갱신 때
        새 언어로 나오므로 여기선 마지막 정적 메시지만 다시 세팅한다.
        """
        # 메뉴 제목.
        self.menu_file.setTitle(self.tr("File"))
        self.menu_analysis.setTitle(self.tr("Analysis"))
        self.menu_modify.setTitle(self.tr("Modify"))
        self.menu_options.setTitle(self.tr("Options"))
        self.menu_help.setTitle(self.tr("Help"))
        self.menu_language.setTitle(self.tr("Language"))

        # Track 액션.
        self.act_add_files.setText(self.tr("Add Files"))
        self.act_add_files.setToolTip(self.tr("Add MP3 files to the list (Ctrl+F)"))
        self.act_add_folder.setText(self.tr("Add Folder"))
        self.act_add_folder.setToolTip(self.tr(
            "Add all MP3 files in a folder (Ctrl+D)"))
        self.act_analyze.setText(self.tr("Track Analysis"))
        self.act_analyze.setToolTip(self.tr(
            "Analyze track gain without applying (Ctrl+T)"))
        self.act_gain.setText(self.tr("Track Gain"))
        self.act_gain.setToolTip(self.tr("Apply track gain to files (Ctrl+G)"))
        self.act_clear.setText(self.tr("Clear All"))
        self.act_clear.setToolTip(self.tr(
            "Clear all files from the list (Ctrl+Shift+Delete)"))

        # Album 액션.
        self.act_album_analyze.setText(self.tr("Album Analysis"))
        self.act_album_analyze.setToolTip(self.tr(
            "Analyze album gain per folder/group without applying (Ctrl+U)"))
        self.act_album_gain.setText(self.tr("Album Gain"))
        self.act_album_gain.setToolTip(self.tr(
            "Apply album gain to files per folder/group (Ctrl+B)"))

        # 분석/수정/옵션 부속 액션.
        self.act_clear_analysis.setText(self.tr("Clear Analysis"))
        self.act_clear_analysis.setToolTip(self.tr(
            "Clear analysis values of selected files (does not change files)"))
        self.act_undo.setText(self.tr("Undo Gain Changes"))
        self.act_undo.setToolTip(self.tr("Undo gain changes of selected files"))
        self.act_each_folder_album.setText(self.tr("Each folder is album"))
        self.act_each_folder_album.setToolTip(self.tr(
            "Treat each folder as a separate album (else all files = one album)"))
        self.act_minimize_to_tray.setText(self.tr("Minimize to tray"))
        self.act_minimize_to_tray.setToolTip(self.tr(
            "When minimized, hide the window and show a system tray icon"))
        self.act_logs.setText(self.tr("Logs..."))
        self.act_logs.setToolTip(self.tr(
            "Configure error / analysis / change log files"))
        self.act_reset_columns.setText(self.tr("Reset Column Widths"))
        self.act_reset_columns.setToolTip(self.tr(
            "Reset all column widths to their defaults"))
        self.act_about.setText(self.tr("About %1").replace("%1", "Gain dB"))
        self.act_about.setToolTip(self.tr(
            "Show program information and license notices"))

        # target 라벨/노트.
        self.lbl_target.setText(self.tr("Target Volume:"))
        self.lbl_target_note.setText(self.tr(
            "(ReplayGain 89 dB reference)"))
        self.lbl_target_note.setToolTip(self.tr(
            "This target is relative to the ReplayGain specification's 89 dB "
            "reference level. It is not an absolute SPL or LUFS level."))
        self.lbl_progress.setText(self.tr("Progress:"))

        # 컨텍스트 메뉴.
        self.ctx_clear_analysis.setText(self.tr("Clear Analysis"))
        self.ctx_undo.setText(self.tr("Undo Gain Changes"))
        self.ctx_remove_tags.setText(self.tr("Remove Tags from Files"))
        self.ctx_play.setText(self.tr("Play MP3 file"))

        # 트레이 메뉴.
        if self._tray is not None:
            self.tray_act_restore.setText(self.tr("Restore"))
            self.tray_act_exit.setText(self.tr("Exit"))
            self._tray.setToolTip("Gain dB")

        # 컬럼 헤더는 model.headerData 가 tr() 하므로 헤더 갱신 신호만.
        self.model.headerDataChanged.emit(
            Qt.Orientation.Horizontal, 0, COLUMN_COUNT - 1)

        # 겸용 버튼·상태바는 현재 상태 기준으로 다시 세팅(정적 부분만).
        self._update_action_states()

    def _build_toolbar(self):
        tb = QToolBar("Main", self)
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_add_files = QAction(self.tr("Add Files"), self)
        self.act_add_files.setShortcut(QKeySequence("Ctrl+F"))
        self.act_add_files.setToolTip(self.tr("Add MP3 files to the list (Ctrl+F)"))
        self.act_add_files.triggered.connect(self._on_add_files)
        tb.addAction(self.act_add_files)

        self.act_add_folder = QAction(self.tr("Add Folder"), self)
        self.act_add_folder.setShortcut(QKeySequence("Ctrl+D"))
        self.act_add_folder.setToolTip(self.tr(
            "Add all MP3 files in a folder (Ctrl+D)"))
        self.act_add_folder.triggered.connect(self._on_add_folder)
        tb.addAction(self.act_add_folder)

        tb.addSeparator()

        self.act_analyze = QAction(self.tr("Track Analysis"), self)
        self.act_analyze.setShortcut(QKeySequence("Ctrl+T"))
        self.act_analyze.setToolTip(self.tr(
            "Analyze track gain without applying (Ctrl+T)"))
        self.act_analyze.triggered.connect(self._on_analyze)
        tb.addAction(self.act_analyze)

        self.act_gain = QAction(self.tr("Track Gain"), self)
        self.act_gain.setShortcut(QKeySequence("Ctrl+G"))
        self.act_gain.setToolTip(self.tr("Apply track gain to files (Ctrl+G)"))
        self.act_gain.triggered.connect(self._on_gain)
        tb.addAction(self.act_gain)

        tb.addSeparator()

        # Album 액션도 툴바에 노출(메뉴와 QAction 공유).
        tb.addAction(self.act_album_analyze)
        tb.addAction(self.act_album_gain)

        tb.addSeparator()

        self.act_clear = QAction(self.tr("Clear All"), self)
        self.act_clear.setShortcut(QKeySequence("Ctrl+Shift+Delete"))
        self.act_clear.setToolTip(self.tr(
            "Clear all files from the list (Ctrl+Shift+Delete)"
        ))
        self.act_clear.triggered.connect(self._on_clear)
        tb.addAction(self.act_clear)

        # 툴바 Track 액션이 준비됐으니 메뉴에 배치(액션 공유).
        self._wire_menu_actions()

    def _build_central(self):
        central = QWidget(self)
        layout = QVBoxLayout(central)

        target_row = QHBoxLayout()
        self.lbl_target = QLabel(self.tr("Target Volume:"))
        target_row.addWidget(self.lbl_target)
        self.spin_target = QDoubleSpinBox(self)
        self.spin_target.setDecimals(1)
        self.spin_target.setSingleStep(1.0)
        self.spin_target.setRange(75.0, 105.0)
        self.spin_target.setValue(DEFAULT_TARGET_DB)
        self.spin_target.setSuffix(" dB")
        self.spin_target.valueChanged.connect(self._on_target_changed)
        target_row.addWidget(self.spin_target)
        self.lbl_target_note = QLabel(self.tr(
            "(ReplayGain 89 dB reference)"))
        self.lbl_target_note.setToolTip(self.tr(
            "This target is relative to the ReplayGain specification's 89 dB "
            "reference level. It is not an absolute SPL or LUFS level."
        ))
        target_row.addWidget(self.lbl_target_note)
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
        # 완전 매끈: 세로 그리드선 끔 + 스타일시트로 셀 테두리·헤더 구분선 제거.
        # 선택 하이라이트가 컬럼 경계 없이 행 전체로 이어진다.
        self.table.setShowGrid(False)
        self.table.setStyleSheet(_TABLE_QSS)
        # 교대 행 색상은 선택색과 뒤섞여 경계가 도드라져 보이므로 끈다.
        self.table.setAlternatingRowColors(False)
        self.table.verticalHeader().setVisible(False)
        self.table.delete_requested.connect(self._on_delete_selected)
        self.table.doubleClicked.connect(self._on_double_click)
        self.table.context_menu_requested.connect(self._show_context_menu)
        header = self.table.horizontalHeader()
        # 전 컬럼 Interactive(드래그한 경계가 그대로 움직이고 다른 컬럼은 유지,
        # 창 밖으로 넘치면 가로 스크롤 — 창 크기와 독립).
        # 마지막 섹션 자동 확장을 꺼야 "드래그 반대편이 움직이는" 현상이 없다.
        header.setStretchLastSection(False)
        for cdef in COLUMNS:
            header.setSectionResizeMode(
                int(cdef.index), QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(int(cdef.index), cdef.default_width)
        self.model.rowsInserted.connect(self._update_action_states)
        self.model.rowsRemoved.connect(self._update_action_states)
        self.model.modelReset.connect(self._update_action_states)
        layout.addWidget(self.table)

        prog_row = QHBoxLayout()
        self.lbl_progress = QLabel(self.tr("Progress:"))
        prog_row.addWidget(self.lbl_progress)
        self.progress = QProgressBar(self)
        self.progress.setValue(0)
        prog_row.addWidget(self.progress, 1)
        self.btn_action = QPushButton(self.tr("Cancel"), self)
        self.btn_action.setEnabled(False)
        self.btn_action.clicked.connect(self._on_action_button)
        prog_row.addWidget(self.btn_action)
        layout.addLayout(prog_row)

        self.setCentralWidget(central)

    def _build_statusbar(self):
        self.statusBar().showMessage(self.tr("Ready"))

    def _build_context_menu(self):
        """우클릭 팝업(MVP 항목)을 구성한다."""
        self.ctx_menu = QMenu(self)

        self.ctx_clear_analysis = QAction(self.tr("Clear Analysis"), self)
        self.ctx_clear_analysis.triggered.connect(self._on_ctx_clear_analysis)
        self.ctx_menu.addAction(self.ctx_clear_analysis)

        self.ctx_menu.addSeparator()

        self.ctx_undo = QAction(self.tr("Undo Gain Changes"), self)
        self.ctx_undo.triggered.connect(self._on_ctx_undo)
        self.ctx_menu.addAction(self.ctx_undo)

        self.ctx_remove_tags = QAction(self.tr("Remove Tags from Files"), self)
        self.ctx_remove_tags.triggered.connect(self._on_ctx_remove_tags)
        self.ctx_menu.addAction(self.ctx_remove_tags)

        self.ctx_menu.addSeparator()

        self.ctx_play = QAction(self.tr("Play MP3 file"), self)
        self.ctx_play.triggered.connect(self._on_ctx_play)
        self.ctx_menu.addAction(self.ctx_play)

    # --- 트레이(최소화→트레이 + 팝업) ---

    def _build_tray(self):
        """시스템 트레이 아이콘과 팝업 메뉴를 구성한다(숨김 상태로 시작).

        트레이 아이콘 자체는 지금 만들어 두되, 최소화→트레이 옵션이 켜져
        실제 최소화가 일어날 때만 show() 한다. 트레이 미지원 환경(드묾)에서는
        옵션이 무효가 되도록 isSystemTrayAvailable 로 방어한다.
        """
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self._tray = None
            return

        icon = app_icon()
        if icon.isNull():
            # 아이콘 파일이 없으면 표준 스타일 아이콘으로 대체(트레이가 비어
            # 보이지 않도록). 기능은 동일.
            icon = self.style().standardIcon(
                QStyle.StandardPixmap.SP_ComputerIcon)

        self._tray = QSystemTrayIcon(icon, self)
        self._tray.setToolTip("Gain dB")

        tray_menu = QMenu()
        self.tray_act_restore = QAction(self.tr("Restore"), self)
        self.tray_act_restore.triggered.connect(self._restore_from_tray)
        tray_menu.addAction(self.tray_act_restore)
        tray_menu.addSeparator()
        self.tray_act_exit = QAction(self.tr("Exit"), self)
        self.tray_act_exit.triggered.connect(self._exit_app)
        tray_menu.addAction(self.tray_act_exit)
        self._tray.setContextMenu(tray_menu)

        # 좌클릭/더블클릭 = 복원. 우클릭은 setContextMenu 가 자동 처리.
        self._tray.activated.connect(self._on_tray_activated)

    def _on_tray_activated(self, reason):
        """트레이 아이콘 클릭. 좌클릭/더블클릭이면 창을 복원한다."""
        if reason in (
            QSystemTrayIcon.ActivationReason.Trigger,
            QSystemTrayIcon.ActivationReason.DoubleClick,
        ):
            self._restore_from_tray()

    def _restore_from_tray(self):
        """트레이에서 창을 복원한다: 트레이 아이콘 숨김 + 창 표시·활성화."""
        if self._tray is not None:
            self._tray.hide()
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _exit_app(self):
        """트레이 Exit: 창을 닫아 정리(설정 저장·워커 종료)한 뒤 앱을 완전히
        종료한다. 트레이 아이콘이 살아 있으면 Qt 이벤트 루프가 유지되어
        self.close() 만으로는 프로세스가 끝나지 않으므로 quit() 를 명시한다.
        """
        self.close()
        QApplication.quit()

    def _on_toggle_tray_option(self, checked: bool):
        """Options → Minimize to tray 토글. 상태만 갱신(다음 최소화부터 적용)."""
        self._minimize_to_tray = bool(checked)
        if not checked and self._tray is not None and self._tray.isVisible():
            # 옵션을 끄는 순간 창이 트레이에 숨어 있으면 되돌린다(잠김 방지).
            self._restore_from_tray()

    def changeEvent(self, event):
        """창 상태 변화 감지(트레이 최소화 + 언어 전환).

        - WindowStateChange: 옵션이 켜져 있고 최소화되면 창을 숨기고 트레이로.
          macOS 는 Dock 최소화 관례라 자동 트레이 이동만 비활성. 트레이 없으면
          무동작.
        - LanguageChange: install_translator 후 Qt 가 흘리는 이벤트. 정적 UI
          문자열을 새 언어로 다시 세팅(_retranslate_ui).
        """
        etype = event.type()
        if etype == QEvent.Type.WindowStateChange:
            if (self._minimize_to_tray
                    and self._tray is not None
                    and not sys.platform.startswith("darwin")
                    and self.isMinimized()):
                # 최소화 순간 트레이로: 아이콘 표시 후 창 숨김. hide 는 다음
                # 이벤트 루프로 미뤄 상태 전이 도중 충돌을 피한다.
                self._tray.show()
                from PySide6.QtCore import QTimer
                QTimer.singleShot(0, self.hide)
        elif etype == QEvent.Type.LanguageChange:
            self._retranslate_ui()
        super().changeEvent(event)

    # --- 설정(컬럼폭·정렬·창 기하·로그·트레이) 저장/복원 ---

    def _load_log_config(self):
        """QSettings 에서 로그 on/off·경로를 복원한다(시작 시)."""
        s = self._settings
        c = self._log_config
        c.error_enabled = s.value("logs/error_enabled", False, type=bool)
        c.error_path = s.value("logs/error_path", "", type=str)
        c.analysis_enabled = s.value("logs/analysis_enabled", False, type=bool)
        c.analysis_path = s.value("logs/analysis_path", "", type=str)
        c.change_enabled = s.value("logs/change_enabled", False, type=bool)
        c.change_path = s.value("logs/change_path", "", type=str)

    def _load_tray_config(self):
        """QSettings 에서 트레이 옵션(minimize_to_tray)을 복원한다(기본 꺼짐)."""
        self._minimize_to_tray = self._settings.value(
            "tray/minimize_to_tray", False, type=bool)

    def _on_open_logs(self):
        """Options → Logs...: 로그 설정 다이얼로그를 연다."""
        dlg = LogsDialog(self._log_config, self)
        dlg.exec()

    def _on_about(self):
        """Help → About: 프로그램 정보 다이얼로그를 연다."""
        dlg = AboutDialog(self)
        dlg.exec()

    def _safe_log(self, func, *args):
        """로그 기록을 호출하되 실패해도 작업을 막지 않는다(상태바로만 안내).

        로그는 부가 기능이라, 파일 쓰기 실패가 분석/적용/undo 본작업을 중단시켜서는
        안 된다(로그 실패 시 안내만 하고 처리는 계속). LogWriteError 를 잡아
        상태바에 한 줄 남기고 넘어간다. 로그 메시지 자체는 영문 고정(합의).
        """
        try:
            func(*args)
        except LogWriteError as exc:
            self.statusBar().showMessage(f"Log write failed: {exc}")

    def _default_window_size(self):
        """저장된 geometry 가 없을 때, 전 컬럼 default_width 합계에 맞춰 초기
        창 가로폭을 정한다(모든 컬럼이 잘리지 않고 딱 보이는 폭). 고정 폼이
        아니라 이 자동 맞춤은 우리 확장이다."""
        total = sum(cdef.default_width for cdef in COLUMNS)

        frame = self.table.frameWidth() * 2
        vbar = self.table.verticalScrollBar().sizeHint().width()
        margins = self.contentsMargins()
        extra = frame + vbar + 4 + margins.left() + margins.right()

        avail = self.screen().availableGeometry()
        width = min(total + extra, avail.width())
        height = max(600, int(avail.height() * 0.6))
        self.resize(width, height)

    def _restore_settings(self):
        """QSettings 에서 창 기하·컬럼폭·정렬 상태를 복원한다(시작 시).

        저장 매체·키는 우리 독립 결정이고 "재기동 시 폭·창 크기·정렬 복원"
        동작만 제공한다. 컬럼폭은 저장 시점 컬럼 수(columns/count)가 현재
        COLUMN_COUNT 와 다르면 통째로 건너뛰어(스키마 불일치 방어)
        default_width 초기값을 유지한다.
        """
        geo = self._settings.value("window/geometry")
        if isinstance(geo, QByteArray) and not geo.isEmpty():
            self.restoreGeometry(geo)
        else:
            self._default_window_size()

        saved_count = self._settings.value("columns/count", type=int)
        if saved_count == COLUMN_COUNT:
            for cdef in COLUMNS:
                key = f"columns/width_{int(cdef.index)}"
                w = self._settings.value(key, type=int)
                if w and w > 0:
                    self.table.setColumnWidth(int(cdef.index), w)

        # 정렬 복원. sortByColumn 재생 -> 프록시/QCollator/None 뒤로 정책이
        # 그대로 태워진다. 저장값 없으면 NAME 오름 유지.
        sort_col = self._settings.value("sort/column", type=int)
        if sort_col is not None and 0 <= sort_col < COLUMN_COUNT:
            order_val = self._settings.value("sort/order", type=int)
            order = (Qt.SortOrder.DescendingOrder if order_val == 1
                     else Qt.SortOrder.AscendingOrder)
            self.table.sortByColumn(sort_col, order)

    def _save_settings(self):
        """창 기하·컬럼폭·정렬·로그·트레이 설정을 QSettings 에 저장한다(창 닫기 시).

        저장 매체·키는 우리 독립 결정이다. 언어(i18n/language)는 선택 순간
        save_language 가 저장하므로 여기선 안 한다.
        """
        self._settings.setValue("window/geometry", self.saveGeometry())

        self._settings.setValue("columns/count", COLUMN_COUNT)
        for cdef in COLUMNS:
            key = f"columns/width_{int(cdef.index)}"
            self._settings.setValue(key, self.table.columnWidth(int(cdef.index)))

        header = self.table.horizontalHeader()
        self._settings.setValue("sort/column", header.sortIndicatorSection())
        order = header.sortIndicatorOrder()
        self._settings.setValue(
            "sort/order", 1 if order == Qt.SortOrder.DescendingOrder else 0)

        c = self._log_config
        self._settings.setValue("logs/error_enabled", c.error_enabled)
        self._settings.setValue("logs/error_path", c.error_path)
        self._settings.setValue("logs/analysis_enabled", c.analysis_enabled)
        self._settings.setValue("logs/analysis_path", c.analysis_path)
        self._settings.setValue("logs/change_enabled", c.change_enabled)
        self._settings.setValue("logs/change_path", c.change_path)

        self._settings.setValue(
            "tray/minimize_to_tray", self._minimize_to_tray)

    def _reset_column_widths(self):
        """모든 컬럼폭을 columns.py 의 default_width 로 되돌린다."""
        for cdef in COLUMNS:
            self.table.setColumnWidth(int(cdef.index), cdef.default_width)
        self.statusBar().showMessage(self.tr("Column widths reset to defaults"))

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
        """작업 중 상태바 문구: "verb k/N - 파일명 - NN.N%".

        verb 는 이미 tr() 된 동사/명사 문자열(호출자가 self.tr 로 넘김). 숫자
        조립은 f-string 유지(작업 중 언어 변경은 드물고 다음 갱신 때 새 언어).
        """
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
                self.btn_action.setText(self.tr("Pause"))
            else:
                self.btn_action.setText(self.tr("Cancel"))
            self.btn_action.setEnabled(True)
        else:
            if self._has_pending():
                self.btn_action.setText(self.tr("Rescan"))
                self.btn_action.setEnabled(True)
            else:
                self.btn_action.setText(self.tr("Cancel"))
                self.btn_action.setEnabled(False)

        if not busy:
            self.statusBar().showMessage(
                self.tr("%n file(s)", "", self.model.rowCount()))

    # --- 겸용 버튼 클릭(Pause / Cancel / Rescan 분기) ---

    def _on_action_button(self):
        """진행바 옆 겸용 버튼. 현재 상태에 따라 pause/cancel/rescan."""
        if self._is_busy():
            if self._worker is not None:
                self._worker.request_cancel()
                self.btn_action.setEnabled(False)
                if self._worker_kind == "scan":
                    self.statusBar().showMessage(
                        self.tr("Pausing after current file..."))
                else:
                    self.statusBar().showMessage(self.tr("Cancelling..."))
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
        """주어진 경로들의 태그를 백그라운드로 스캔한다(파일 추가 시 태그 채우기)."""
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
            f"{self.tr('Scanning tags')} {self._scan_offset}/{total}")
        self._worker.start()

    # --- 파일 추가 공통 ---

    def _add_from(self, paths):
        if self._is_busy():
            self.statusBar().showMessage(
                self.tr("Busy - wait for the current task"))
            return
        mp3s = collect_mp3_paths(paths, recurse=True)
        if not mp3s:
            self.statusBar().showMessage(self.tr("No .mp3 files found"))
            return
        new_rows = self.model.add_paths(mp3s)
        if not new_rows:
            self.statusBar().showMessage(
                f"{self.tr('No new files')}, "
                f"{self.model.rowCount()} {self.tr('total')}"
            )
            return
        # 파일 목록이 바뀌었으니 앨범 씨앗을 통째로 무효화.
        self._invalidate_album_seeds()
        self.statusBar().showMessage(
            f"{self.tr('Added')} {len(new_rows)} {self.tr('file(s)')}, "
            f"{self.model.rowCount()} {self.tr('total')} - "
            f"{self.tr('scanning tags...')}"
        )
        self._start_tag_scan(self._pending_paths())

    # --- 툴바/메뉴 액션 ---

    def _on_add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, self.tr("Add MP3 files"), "",
            self.tr("MP3 files (*.mp3);;All files (*.*)")
        )
        if files:
            self._add_from(files)

    def _on_add_folder(self):
        folder = QFileDialog.getExistingDirectory(self, self.tr("Add folder"))
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
            self.statusBar().showMessage(self.tr(
                "Nothing to analyze (all selected files already have values)"
            ))
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
        self.statusBar().showMessage(
            f"{self.tr('Analyzing')} {len(paths)} {self.tr('file(s)...')}")
        self._worker.start()

    def _on_gain(self):
        """Track Gain 적용. ApplyWorker 로 위임한다."""
        if self._is_busy():
            return

        rows = self._target_source_rows()
        paths = []
        seed_results = {}
        for r in rows:
            fr = self.model.get_row(r)
            if fr is None:
                continue
            paths.append(fr.path)
            seed_results[fr.path] = fr.result

        if not paths:
            self.statusBar().showMessage(self.tr(
                "Nothing to apply (all target files already at target)"
            ))
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
        self.statusBar().showMessage(
            f"{self.tr('Applying gain to')} {len(paths)} {self.tr('file(s)...')}")
        self._worker.start()

    # --- Album Analysis / Album Gain 핸들러 ---

    def _on_album_analyze(self):
        """Album Analysis. 선택(없으면 전체) 전부 분석."""
        if self._is_busy():
            return

        rows = self._target_source_rows()
        paths = []
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                paths.append(fr.path)

        if not paths:
            self.statusBar().showMessage(self.tr("No files to analyze"))
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
        self.statusBar().showMessage(
            f"{self.tr('Analyzing')} {len(paths)} {self.tr('file(s) in')} "
            f"{len(groups)} {self.tr('album(s)...')}")
        self._worker.start()

    def _on_album_gain(self):
        """Album Gain 적용. AlbumApplyWorker 위임."""
        if self._is_busy():
            return

        rows = self._target_source_rows()
        paths = []
        for r in rows:
            fr = self.model.get_row(r)
            if fr is not None:
                paths.append(fr.path)

        if not paths:
            self.statusBar().showMessage(self.tr("No files to apply"))
            return

        each_folder = self.act_each_folder_album.isChecked()
        groups = group_by_album(paths, each_folder_is_album=each_folder)
        # 대상 경로에 해당하는 씨앗만 추려 넘긴다(나머지는 워커가 분석).
        seed_raws = {p: self._album_raws[p]
                     for p in paths if p in self._album_raws}

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
            f"{self.tr('Applying album gain to')} {len(paths)} "
            f"{self.tr('file(s) in')} {len(groups)} {self.tr('album(s)...')}")
        self._worker.start()

    def _on_clear(self):
        """Clear 버튼/단축키: 목록 전체 삭제."""
        if self._is_busy():
            return
        self.model.clear()
        self._invalidate_album_seeds()

    def _on_delete_selected(self):
        """Delete 키: 선택 행만 삭제. 선택 없으면 무동작."""
        if self._is_busy():
            return
        rows = self._selected_source_rows()
        if rows:
            self.model.remove_rows(rows)
            self._invalidate_album_seeds()

    def _on_double_click(self, index: QModelIndex):
        """더블클릭한 곡을 OS 기본 앱으로 연다."""
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
            self.statusBar().showMessage(f"{self.tr('File not found:')} {fr.path}")
            return
        try:
            open_with_default_app(fr.path)
        except Exception as exc:
            self.statusBar().showMessage(f"{self.tr('Could not open file:')} {exc}")

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
        self.statusBar().showMessage(
            f"{self.tr('Target set to')} {value:.1f} dB")

    # --- 우클릭 팝업 표시 + 항목 핸들러 ---

    def _show_context_menu(self, global_pos):
        """우클릭 팝업을 선택·busy 상태에 맞춰 활성화한 뒤 표시."""
        has_sel = len(self.table.selectionModel().selectedRows()) > 0
        busy = self._is_busy()
        enable = has_sel and not busy
        self.ctx_clear_analysis.setEnabled(enable)
        self.ctx_undo.setEnabled(enable)
        self.ctx_remove_tags.setEnabled(enable)
        self.ctx_play.setEnabled(enable)
        self.ctx_menu.exec(global_pos)

    def _on_ctx_clear_analysis(self):
        """선택 행의 표시값만 리셋(파일 미변경)."""
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
                f"{self.tr('Cleared analysis of')} {len(rows)} "
                f"{self.tr('file(s)')}")

    def _on_ctx_undo(self):
        """선택 행의 게인 변경을 undo(파일 변경)."""
        self._start_file_action("undo")

    def _on_ctx_remove_tags(self):
        """선택 행의 mp3gain 태그 제거(파일 변경)."""
        self._start_file_action("remove_tags")

    def _on_ctx_play(self):
        """선택 행(들)을 기본 앱으로 연다."""
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
            self.statusBar().showMessage(self.tr("No files selected"))
            return

        self._action_done = 0
        self._failed_count = 0
        self._batch_total = len(paths)
        self._action_verb = (self.tr("Undoing") if action == "undo"
                             else self.tr("Removing tags"))
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
        self.statusBar().showMessage(
            f"{self._action_verb} {len(paths)} {self.tr('file(s)...')}")
        self._worker.start()

    # --- 태그 스캔 워커 슬롯 ---

    def _on_scan_current(self, path: str):
        done = self._scan_offset + self._scanned_count
        self.statusBar().showMessage(
            f"{self.tr('Scanning tags')} {done}/{self._scan_total} - "
            f"{os.path.basename(path)}")

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
                f"{self.tr('Paused - scanned')} {self._scan_offset + done}/"
                f"{total} {self.tr('tag(s). Press Rescan to continue.')}"
            )
        else:
            self.progress.setRange(0, total)
            self.progress.setValue(total)
            self.statusBar().showMessage(
                f"{self.tr('Tag scan done -')} {total} {self.tr('file(s) total')}"
            )

    # --- 분석 워커 슬롯(Track Analysis + Album Analysis 공유) ---

    def _on_analyze_current(self, path: str):
        self._current_name = os.path.basename(path)
        self._current_fraction = 0.0
        self.statusBar().showMessage(
            self._batch_status(self.tr("Analyzing"), self._progress_base + 1))

    def _on_analyze_file_progress(self, fraction: float):
        self._current_fraction = fraction
        self._set_batch_progress(self._progress_base, fraction)
        self.statusBar().showMessage(
            self._batch_status(self.tr("Analyzing"), self._progress_base + 1))

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
        # Analysis Log: 분석된 Track dB·MaxAmp 기록.
        if result.get("status") == "ok" and result.get("track_db") is not None:
            self._safe_log(
                log_analysis_track, self._log_config, path,
                result.get("track_db"), result.get("curr_max_amp") or 0.0)

    def _on_worker_failed(self, path: str, msg: str):
        self._failed_count += 1
        # Error Log: 오류 한 건 기록(행 유무와 무관하게 남긴다).
        self._safe_log(log_error, self._log_config, f"{path}: {msg}")
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
        parts = [f"{self.tr('Analyzed')} {done} {self.tr('file(s)')}"]
        if failed:
            parts.append(f"{failed} {self.tr('failed')}")
        msg = ", ".join(parts)
        self.statusBar().showMessage(
            f"{self.tr('Cancelled -')} {msg}" if cancelled else msg)

    # --- 앨범 고유 슬롯 ---

    def _on_album_row_raw(self, path: str, raw: dict):
        """앨범 곡 원재료를 씨앗으로 보관(Album Gain 재사용용). 모델 미변경."""
        self._album_raws[path] = raw

    def _on_album_group_done(self, key: str, agg: dict):
        """한 앨범 그룹의 집계 완료(Analysis Log 에 AlbumdB 기록).

        표시는 row_done(_on_worker_row_done)이 곡별로 처리한다. 여기서는 그룹의
        album_db 를 로그에만 남긴다(모델 미변경). 앨범 dB 는 그룹당 하나라
        그룹 단위로 한 줄(대표 key)만 남긴다 - 중복을 줄인 것(합의, 10.2
        로그 가독성).
        """
        if agg.get("status") == "ok" and agg.get("album_db") is not None:
            self._safe_log(
                log_analysis_album, self._log_config, str(key),
                agg.get("album_db"))

    # --- 적용 워커 슬롯(Track Gain + Album Gain 공유) ---

    def _on_apply_current(self, path: str):
        self._current_name = os.path.basename(path)
        self._current_fraction = 0.0
        if self._album_applying:
            return
        _label = (self.tr("Analyzing")
                  if isinstance(self._worker, AlbumApplyWorker)
                  else self.tr("Applying"))
        self.statusBar().showMessage(
            self._batch_status(_label, self._progress_base + 1))

    def _on_apply_file_progress(self, fraction: float):
        self._current_fraction = fraction
        self._set_batch_progress(self._progress_base, fraction)
        if self._album_applying:
            return
        _label = (self.tr("Analyzing")
                  if isinstance(self._worker, AlbumApplyWorker)
                  else self.tr("Applying"))
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
            self._batch_status(self.tr("Applying"), done))

    def _on_apply_analyzed(self, path: str, result: dict):
        """워커가 no_change 로 넘긴 행(코어가 이미 최신 태그로 판단해 파일을
        기록하지 않음). 파일 변경 없이 분석 결과 표시만 반영한다."""
        self._analyzed_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.set_result(result)
        self.model.row_changed(r)

    def _on_apply_applied(self, path: str, result: dict, steps: int = 0):
        """실제 게인이 적용된 행. shift 반영된 표시 dict 로 갱신 + Change Log.

        steps 는 워커가 실제 적용한 스텝(Track/Album 공유). Change Log 에
        steps × 정밀 dB 로 남긴다. steps==0 이면 log_change 가 내부에서
        no-op(변경 없음은 기록 안 함).
        """
        self._applied_count += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            return
        fr = self.model.get_row(r)
        fr.mark_applied(result)
        self.model.row_changed(r)
        self._safe_log(log_change, self._log_config, path, steps)

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
        parts = [f"{self.tr('Applied gain to')} {applied} {self.tr('file(s)')}"]
        if analyzed_only:
            parts.append(f"{analyzed_only} {self.tr('already at target')}")
        if failed:
            parts.append(f"{failed} {self.tr('failed')}")
        msg = ", ".join(parts)
        self.statusBar().showMessage(
            f"{self.tr('Cancelled -')} {msg}" if cancelled else msg)

    # --- 파일 액션 워커 슬롯(undo / remove_tags) ---

    def _on_action_current(self, path: str):
        self.statusBar().showMessage(
            f"{self._action_verb} {self._action_done}/{self._batch_total} - "
            f"{os.path.basename(path)}")

    def _on_action_progress(self, done: int, total: int):
        self.progress.setValue(done)

    def _on_action_undone(self, path: str, undo_steps: int):
        """undo 성공: 되돌린 스텝으로 표시를 갱신.

        Change Log 에 undo 스텝을 기록한다(undo 도 Change Log 로 남긴다).
        """
        self._action_done += 1
        r = self.model.find_row_by_path(path)
        if r is None:
            self._safe_log(log_change, self._log_config, path, undo_steps)
            return
        fr = self.model.get_row(r)
        if fr.result and fr.result.get("status") == "ok" \
                and fr.result.get("track_db") is not None:
            fr.result = shift_after_apply(fr.result, undo_steps)
            self.model.row_changed(r)
        self._safe_log(log_change, self._log_config, path, undo_steps)

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
        verb_done = (self.tr("Undone") if self._action_verb == self.tr("Undoing")
                     else self.tr("Removed tags from"))
        parts = [f"{verb_done} {done} {self.tr('file(s)')}"]
        if failed:
            parts.append(f"{failed} {self.tr('failed')}")
        msg = ", ".join(parts)
        self.statusBar().showMessage(
            f"{self.tr('Cancelled -')} {msg}" if cancelled else msg)

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

    # --- 창 닫기: 설정 저장 + 실행 중 워커 안전 종료 ---

    def closeEvent(self, event):
        """창을 닫을 때 설정을 저장하고 실행 중인 워커를 취소·대기시킨 뒤 닫는다.

        X(닫기)는 실제 종료다(트레이로 보내지 않음). 트레이 아이콘이 떠 있으면
        함께 정리한다.
        """
        self._save_settings()
        if self._tray is not None:
            self._tray.hide()
        w = self._worker
        if w is not None:
            w.request_cancel()
            if not w.wait(10000):
                w.terminate()
                w.wait()
        super().closeEvent(event)