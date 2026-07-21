r"""gui/columns.py — 리스트뷰 컬럼 정의(상수 테이블).

원본 MP3GainGUI frmMain 의 컬럼 구성을 관찰해 정의한다. MVP 는 Track 묶음
(Volume / Track Gain / clipping)에 더해 Album 묶음(Album Volume / Album Gain /
clip(Album))을 원본 순서대로 노출한다:
  Path\File / Volume / Track Gain / clipping /
  Album Volume / Album Gain / clip(Album) / Curr Max Amp
(원본은 clip(Track)·Max Noclip 도 있으나 MVP 제외 — CLAUDE.md 참조. 원본
컬럼 순서상 Track 묶음 뒤에 Album 묶음, 맨 끝이 Curr Max Amp.)

헤더 문자열은 원본 관찰값(영문) 그대로 둔다. 다국어화는 GUI 계층의 tr()
책임이며 후속 작업이다(CLAUDE.md 8단계 합의). 정렬·표시 배선은 model 의
_display_text/_sort_value 가 담당하므로 sort_key 필드는 현재 쓰이지 않으나,
ColumnDef 시그니처 유지를 위해 채워 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from PySide6.QtCore import Qt


class Col(IntEnum):
    """컬럼 인덱스(모델 columnCount 와 순서의 단일 출처).

    원본 컬럼 순서 재현: Track 묶음 → Album 묶음 → Curr Max Amp.
    """
    NAME = 0
    VOLUME = 1
    TRACK_GAIN = 2
    CLIP = 3
    ALBUM_VOLUME = 4
    ALBUM_GAIN = 5
    ALBUM_CLIP = 6
    MAX_AMP = 7


@dataclass(frozen=True)
class ColumnDef:
    """한 컬럼의 정의.

    index    : Col 값(위치).
    header   : 헤더 표기(영문, tr 은 후속).
    align    : 셀 정렬 플래그(Qt.AlignmentFlag).
    sort_key : FileRow 를 받아 정렬용 값을 돌려주는 함수(현재 미사용, 준비만).
    """
    index: Col
    header: str
    align: Qt.AlignmentFlag
    sort_key: Callable[[object], object]


# 정렬키 헬퍼(현재 미사용): 미분석/None 은 뒤로 가도록 보수적 기본값.
def _num_or_min(value):
    return value if value is not None else float("-inf")


_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
_CENTER = Qt.AlignmentFlag.AlignCenter


COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef(Col.NAME, "Path\\File", _LEFT,
              lambda row: str(getattr(row, "path", "")).lower()),
    ColumnDef(Col.VOLUME, "Volume", _RIGHT,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.TRACK_GAIN, "Track Gain", _RIGHT,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.CLIP, "clipping", _CENTER,
              lambda row: ""),
    ColumnDef(Col.ALBUM_VOLUME, "Album Volume", _RIGHT,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.ALBUM_GAIN, "Album Gain", _RIGHT,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.ALBUM_CLIP, "clip(Album)", _CENTER,
              lambda row: ""),
    ColumnDef(Col.MAX_AMP, "Curr Max Amp", _RIGHT,
              lambda row: _num_or_min(None)),
)

COLUMN_COUNT = len(COLUMNS)
