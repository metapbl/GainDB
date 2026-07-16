"""gui/model.py — 파일 목록 테이블 모델.

FileRow: 파일 한 개의 상태. gaindb.api.analyze_file 이 돌려준 dict 를 통째로
보관하고(raw 값이 재계산의 씨앗), GUI 전용 필드(경로·상태·에러)만 얹는다.
dict 키를 바깥에서 직접 만지지 않도록 헬퍼(get/set_result/clear_result)를 둔다.

FileTableModel: QAbstractTableModel. 표시 포맷과 3색(clip 색상)을 담당하되,
모든 수치는 api 가 계산한 값을 표시만 한다(GUI 무계산 원칙). 3색은 원본
DispJunk 의 vbBlack/vbBlue/vbRed 동작을 관찰해 독립 구현(색값은 저작권 비대상).
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

from PySide6.QtCore import QAbstractTableModel, QModelIndex, Qt
from PySide6.QtGui import QColor

from gui.columns import COLUMNS, COLUMN_COUNT, Col


# clip_state → 글자색(원본 DispJunk 대응). 색값은 관찰된 동작이라 차용 가능.
_CLIP_COLOR = {
    "none": QColor(Qt.GlobalColor.black),
    "possible": QColor(Qt.GlobalColor.blue),
    "definite": QColor(Qt.GlobalColor.red),
}

# clip 컬럼에 보일 문자열(원본 strClipYes="Y" / strClipMaybe="???").
_CLIP_TEXT = {"none": "", "possible": "???", "definite": "Y"}

# 빈 값 표시(원본은 " " 를 넣어 컬럼 폭을 유지).
_BLANK = " "


@dataclass
class FileRow:
    """리스트의 한 행(파일 하나).

    path         : 절대 경로(고유 식별자).
    result       : analyze_file 결과 dict. 미분석이면 None.
    status       : "pending" | "analyzed" | "applied" | "error" | "no_samples".
    error_msg    : 에러 시 사람이 읽을 메시지(없으면 None).
    """
    path: str
    result: dict | None = None
    status: str = "pending"
    error_msg: str | None = None

    @property
    def display_name(self) -> str:
        # MVP 는 전체 경로 표기(원본 기본 PATHFILE). 파일명만/경로분리 표기는 후속.
        return self.path

    @property
    def clip_state(self) -> str:
        if self.result is None:
            return "none"
        return self.result.get("clip_state", "none")

    def get(self, key, default=None):
        """result dict 에서 값 하나를 안전하게 꺼낸다(미분석이면 default)."""
        if self.result is None:
            return default
        return self.result.get(key, default)

    def set_result(self, result: dict) -> None:
        """분석/재계산 결과를 반영하고 status 를 갱신한다."""
        self.result = result
        self.error_msg = None
        if result.get("status") == "not_enough_samples":
            self.status = "no_samples"
        else:
            self.status = "analyzed"

    def mark_applied(self, result: dict) -> None:
        """적용 후(shift_after_apply 결과 등)를 반영한다."""
        self.result = result
        self.error_msg = None
        self.status = "applied"

    def mark_error(self, message: str) -> None:
        self.error_msg = message
        self.status = "error"

    def clear_result(self) -> None:
        """분석 결과를 지우고 pending 으로 되돌린다(원본 Clear Analysis)."""
        self.result = None
        self.error_msg = None
        self.status = "pending"


def _fmt_db(value) -> str:
    """dB 값 표시(원본 Format$(..., "0.0")). None 이면 빈칸."""
    if value is None:
        return _BLANK
    return f"{value:.1f}"


def _fmt_int(value) -> str:
    if value is None:
        return _BLANK
    return f"{int(value)}"


class FileTableModel(QAbstractTableModel):
    """파일 행들을 담는 테이블 모델(표시 전용)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows: list[FileRow] = []

    # --- Qt 필수 오버라이드 ---

    def rowCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return len(self._rows)

    def columnCount(self, parent=QModelIndex()) -> int:
        if parent.isValid():
            return 0
        return COLUMN_COUNT

    def headerData(self, section, orientation, role=Qt.ItemDataRole.DisplayRole):
        if orientation != Qt.Orientation.Horizontal:
            return None
        if role == Qt.ItemDataRole.DisplayRole:
            return COLUMNS[section].header
        return None

    def data(self, index, role=Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None
        row = self._rows[index.row()]
        col = index.column()

        if role == Qt.ItemDataRole.DisplayRole:
            return self._display_text(row, col)

        if role == Qt.ItemDataRole.ForegroundRole:
            # 원본 DispJunk: clip 상태에 따라 행 전체 글자색을 바꾼다.
            return _CLIP_COLOR.get(row.clip_state)

        if role == Qt.ItemDataRole.TextAlignmentRole:
            return int(COLUMNS[col].align)

        if role == Qt.ItemDataRole.ToolTipRole and col == Col.NAME:
            if row.status == "error" and row.error_msg:
                return row.error_msg
            return row.path

        return None

    # --- 표시 텍스트 계산(포맷만, 수치 계산 없음) ---

    def _display_text(self, row: FileRow, col: int) -> str:
        if col == Col.NAME:
            return os.path.basename(row.path) if row.status == "error" \
                else row.display_name
        if col == Col.VOLUME:
            return _fmt_db(row.get("volume"))
        if col == Col.TRACK_GAIN:
            return _fmt_db(row.get("track_gain_db"))
        if col == Col.CLIP:
            return _CLIP_TEXT.get(row.clip_state, "")
        if col == Col.MAX_AMP:
            return _fmt_int(row.get("curr_max_amp"))
        return ""

    # --- 행 관리 API (윈도우/워커가 사용) ---

    def rows(self) -> list[FileRow]:
        return self._rows

    def row_at(self, i: int) -> FileRow:
        return self._rows[i]

    def index_of_path(self, path: str) -> int:
        for i, r in enumerate(self._rows):
            if r.path == path:
                return i
        return -1

    def add_paths(self, paths) -> int:
        """중복(경로 기준)을 제외하고 행을 추가한다. 추가된 개수를 반환."""
        existing = {r.path for r in self._rows}
        new_paths = [p for p in paths if p not in existing]
        if not new_paths:
            return 0
        start = len(self._rows)
        self.beginInsertRows(QModelIndex(), start, start + len(new_paths) - 1)
        self._rows.extend(FileRow(path=p) for p in new_paths)
        self.endInsertRows()
        return len(new_paths)

    def remove_rows(self, indexes) -> None:
        """주어진 행 인덱스들을 제거한다(내림차순 처리로 인덱스 안정)."""
        for i in sorted(set(indexes), reverse=True):
            if 0 <= i < len(self._rows):
                self.beginRemoveRows(QModelIndex(), i, i)
                del self._rows[i]
                self.endRemoveRows()

    def clear(self) -> None:
        if not self._rows:
            return
        self.beginRemoveRows(QModelIndex(), 0, len(self._rows) - 1)
        self._rows.clear()
        self.endRemoveRows()

    def row_changed(self, i: int) -> None:
        """i 번째 행의 표시를 갱신하라고 뷰에 알린다(워커 결과 반영 후 호출)."""
        if 0 <= i < len(self._rows):
            top = self.index(i, 0)
            bottom = self.index(i, COLUMN_COUNT - 1)
            self.dataChanged.emit(top, bottom)
