"""Qt table model for the MP3 gain file list (clean-room)."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any, Optional

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from gui.columns import COLUMNS, COLUMN_COUNT, Col

# Custom role used by the sort proxy to fetch the raw (typed) sort value
# instead of the formatted display string.
SORT_ROLE = int(Qt.ItemDataRole.UserRole) + 1


@dataclass
class FileRow:
    """One entry in the file list.

    `result` holds the full dict returned by api.analyze_file / read_file_tags
    / compute_album_display (or None until scanned). Album 표시값(album_* 키)은
    Album Analysis 후에만 채워진다(그 전엔 Album 컬럼이 빈칸).
    """

    path: str
    result: Optional[dict] = None
    status: str = "pending"  # pending | analyzed | applied | error
    error_msg: str = ""
    tag_scanned: bool = False

    def set_result(self, result: dict) -> None:
        self.result = result
        self.status = "analyzed"
        self.error_msg = ""
        self.tag_scanned = True

    def mark_applied(self, result: dict) -> None:
        self.result = result
        self.status = "applied"
        self.error_msg = ""

    def mark_error(self, msg: str) -> None:
        self.status = "error"
        self.error_msg = msg

    def clear_result(self) -> None:
        """표시값·status 를 리셋해 미분석(빈칸) 상태로 되돌린다(파일 미변경).

        우클릭 Clear Analysis 와 태그 제거(Remove Tags) 후 호출된다. tag_scanned
        는 True 로 유지한다(Rescan 은 대량 추가 태그 스캔 Pause→재개 전용).
        """
        self.result = None
        self.status = "pending"
        self.error_msg = ""

    def set_tag_result(self, result: dict) -> None:
        """파일 추가 시 태그 스캔 결과를 반영한다(원본 AddSingleFile 대응)."""
        self.result = result
        self.error_msg = ""
        self.status = "analyzed" if result.get("status") == "ok" else "pending"
        self.tag_scanned = True

    def needs_tag_scan(self) -> bool:
        """태그 스캔(또는 Rescan) 대상인지. 아직 태그 스캔을 시도하지 않은 행."""
        return not self.tag_scanned

    def needs_analysis(self) -> bool:
        """Track Analysis 대상인지(값이 아직 없는지). 원본 RadiodBGain=NOREALNUM."""
        return self.status not in ("analyzed", "applied")

    def needs_album_analysis(self) -> bool:
        """Album Analysis 대상인지(앨범 표시값 album_* 이 아직 없는지).

        원본 AlbumdBGain=NOREALNUM 대응. result 가 있고 status 가 ok 여도
        album_db 가 없으면 앨범 분석이 필요하다(Track 분석만 된 상태). 태그에서
        album_gain 을 읽은 경우는 read_file_tags 확장 시 album_db 가 채워진다
        (그 배선은 4단계 GUI 에서). 지금은 album_db 유무로만 판정한다.
        """
        r = self.result
        if not r or r.get("status") != "ok":
            return True
        return r.get("album_db") is None


def _fmt_db(value: Optional[float]) -> str:
    return "" if value is None else f"{value:.1f}"


def _fmt_int(value: Optional[int]) -> str:
    return "" if value is None else str(value)


# Warning colors only. "none" is intentionally left unset so the OS palette
# supplies the correct text color (fixes invisible black text in dark mode).
_CLIP_COLORS = {
    "possible": QColor(0, 0, 255),   # blue
    "definite": QColor(255, 0, 0),   # red
}

_CLIP_TEXT = {
    "none": "",
    "possible": "?",
    "definite": "clip",
}


class FileTableModel(QAbstractTableModel):
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._rows: list[FileRow] = []
        self._seen: set[str] = set()
        # path -> row index. 워커 시그널의 path->행 역참조를 O(1) 로.
        self._index: dict[str, int] = {}

    # ---- Qt required overrides -------------------------------------------
    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else len(self._rows)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 0 if parent.isValid() else COLUMN_COUNT

    def headerData(self, section: int, orientation, role=Qt.ItemDataRole.DisplayRole):
        if role != Qt.ItemDataRole.DisplayRole:
            return None
        if orientation == Qt.Orientation.Horizontal:
            return COLUMNS[section].header
        return None

    def data(self, index: QModelIndex, role=Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = COLUMNS[index.column()]

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_text(row, col.index)

        if role == SORT_ROLE:
            return self._sort_value(row, col.index)

        if role == Qt.ItemDataRole.ForegroundRole:
            # Track clip 은 clip_state, Album clip 은 album_clip_state 로 색칠.
            if row.result:
                if col.index == Col.CLIP:
                    return _CLIP_COLORS.get(row.result.get("clip_state"))
                if col.index == Col.ALBUM_CLIP:
                    return _CLIP_COLORS.get(row.result.get("album_clip_state"))
            return None

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(col.align)

        if role == Qt.ItemDataRole.ToolTipRole:
            if row.status == "error" and row.error_msg:
                return row.error_msg
            if col.index == Col.NAME:
                return row.path
            return None

        return None

    # ---- display / sort helpers -----------------------------------------
    def _display_text(self, row: FileRow, key: Col) -> str:
        if key == Col.NAME:
            return row.path  # full path + filename (matches original mp3gain)

        r = row.result
        if not r:
            return ""  # un-scanned rows show empty cells

        if key == Col.VOLUME:
            return _fmt_db(r.get("volume"))
        if key == Col.TRACK_GAIN:
            return _fmt_db(r.get("track_gain_db"))
        if key == Col.CLIP:
            return _CLIP_TEXT.get(r.get("clip_state"), "")
        if key == Col.ALBUM_VOLUME:
            return _fmt_db(r.get("album_volume"))
        if key == Col.ALBUM_GAIN:
            return _fmt_db(r.get("album_gain_db"))
        if key == Col.ALBUM_CLIP:
            return _CLIP_TEXT.get(r.get("album_clip_state"), "")
        if key == Col.MAX_AMP:
            return _fmt_int(r.get("curr_max_amp"))
        return ""

    def _sort_value(self, row: FileRow, key: Col) -> Any:
        if key == Col.NAME:
            return row.path

        r = row.result
        if not r:
            return None  # let the proxy decide placement of empties

        if key == Col.VOLUME:
            return r.get("volume")
        if key == Col.TRACK_GAIN:
            return r.get("track_gain_db")
        if key == Col.CLIP:
            return r.get("clip_state", "")
        if key == Col.ALBUM_VOLUME:
            return r.get("album_volume")
        if key == Col.ALBUM_GAIN:
            return r.get("album_gain_db")
        if key == Col.ALBUM_CLIP:
            return r.get("album_clip_state", "")
        if key == Col.MAX_AMP:
            return r.get("curr_max_amp")
        return None

    # ---- row management --------------------------------------------------
    def add_paths(self, paths: list[str]) -> list[int]:
        """새 경로를 행으로 추가하고, 추가된 행들의 모델 인덱스 목록을 반환한다."""
        new = [p for p in paths if p not in self._seen]
        if not new:
            return []
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(new) - 1)
        for i, p in enumerate(new):
            self._rows.append(FileRow(path=p))
            self._seen.add(p)
            self._index[p] = start + i
        self.endInsertRows()
        return list(range(start, start + len(new)))

    def remove_rows(self, rows: list[int]) -> None:
        removed = False
        for r in sorted(set(rows), reverse=True):
            if 0 <= r < len(self._rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                self._seen.discard(self._rows[r].path)
                del self._rows[r]
                self.endRemoveRows()
                removed = True
        if removed:
            self._rebuild_index()

    def clear(self) -> None:
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self._seen.clear()
        self._index.clear()
        self.endResetModel()

    def _rebuild_index(self) -> None:
        """path->row index 맵을 현재 _rows 로부터 다시 세운다(삭제 후 호출)."""
        self._index = {row.path: i for i, row in enumerate(self._rows)}

    def row_changed(self, row: int) -> None:
        if 0 <= row < len(self._rows):
            top = self.index(row, 0)
            bot = self.index(row, COLUMN_COUNT - 1)
            self.dataChanged.emit(top, bot)

    def get_row(self, row: int) -> Optional[FileRow]:
        if 0 <= row < len(self._rows):
            return self._rows[row]
        return None

    def find_row_by_path(self, path: str) -> Optional[int]:
        """경로로 모델 행 인덱스를 찾는다(워커 시그널의 path->행 역참조용, O(1))."""
        return self._index.get(path)

    def row_count(self) -> int:
        return len(self._rows)
