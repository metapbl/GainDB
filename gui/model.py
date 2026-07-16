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
    (or None until scanned). GUI-only bookkeeping lives in the other fields.
    """

    path: str
    result: Optional[dict] = None
    status: str = "pending"  # pending | analyzed | applied | error
    error_msg: str = ""

    def set_result(self, result: dict) -> None:
        self.result = result
        self.status = "analyzed"
        self.error_msg = ""

    def mark_applied(self, result: dict) -> None:
        self.result = result
        self.status = "applied"
        self.error_msg = ""

    def mark_error(self, msg: str) -> None:
        self.status = "error"
        self.error_msg = msg

    def clear_result(self) -> None:
        self.result = None
        self.status = "pending"
        self.error_msg = ""

    def set_tag_result(self, result: dict) -> None:
        """파일 추가 시 태그 스캔 결과를 반영한다(원본 AddSingleFile 대응).

        태그에서 값을 읽었으면(status="ok") 분석 불필요 상태로, 태그가 없으면
        (status="no_tag") 분석 필요 상태로 둔다. 어느 쪽이든 result 는 보관해
        표시(빈칸 또는 값)에 쓴다.
        """
        self.result = result
        self.error_msg = ""
        self.status = "analyzed" if result.get("status") == "ok" else "pending"

    def needs_analysis(self) -> bool:
        """Track Analysis 대상인지(값이 아직 없는지). 원본 RadiodBGain=NOREALNUM.

        이미 분석/적용됐거나 태그에서 값을 읽었으면(status="analyzed"/"applied")
        대상이 아니다. 그 외(pending/no_tag/error)는 분석이 필요하다.
        """
        return self.status not in ("analyzed", "applied")


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
            if col.index == Col.CLIP and row.result:
                return _CLIP_COLORS.get(row.result.get("clip_state"))
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
        if key == Col.MAX_AMP:
            return r.get("curr_max_amp")
        return None

    # ---- row management --------------------------------------------------
    def add_paths(self, paths: list[str]) -> list[int]:
        """새 경로를 행으로 추가하고, 추가된 행들의 모델 인덱스 목록을 반환한다.

        반환값(추가된 행 인덱스)은 호출자가 곧바로 태그 스캔 결과를 채우는 데
        쓴다(원본 AddSingleFile 이 추가 직후 DispJunk 하던 동작 대응).
        """
        new = [p for p in paths if p not in self._seen]
        if not new:
            return []
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(new) - 1)
        for p in new:
            self._rows.append(FileRow(path=p))
            self._seen.add(p)
        self.endInsertRows()
        return list(range(start, start + len(new)))

    def remove_rows(self, rows: list[int]) -> None:
        for r in sorted(set(rows), reverse=True):
            if 0 <= r < len(self._rows):
                self.beginRemoveRows(QModelIndex(), r, r)
                self._seen.discard(self._rows[r].path)
                del self._rows[r]
                self.endRemoveRows()

    def clear(self) -> None:
        if not self._rows:
            return
        self.beginResetModel()
        self._rows.clear()
        self._seen.clear()
        self.endResetModel()

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
        """경로로 모델 행 인덱스를 찾는다(워커 시그널의 path→행 역참조용).

        정렬 프록시·삭제로 뷰 인덱스가 흔들려도 path 는 안정적이므로,
        워커는 path 로 결과를 돌려주고 여기서 원본 모델 행을 되찾는다.
        없으면 None(그 사이 삭제된 경우).
        """
        for i, row in enumerate(self._rows):
            if row.path == path:
                return i
        return None

    def row_count(self) -> int:
        return len(self._rows)
