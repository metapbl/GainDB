"""gui/columns.py — MVP 리스트뷰 컬럼 정의(상수 테이블).

원본 MP3GainGUI frmMain 의 컬럼 구성을 관찰해 MVP 5개만 정의한다:
  파일명 / Volume / Track Gain / clipping / Curr Max Amp
(Album 계열·Max Noclip·clip(Track/Album) 등은 MVP 제외 — CLAUDE.md 6단계 8번.)

헤더 문자열은 원본 관찰값(영문) 그대로 둔다. 다국어화는 GUI 계층의 tr()
책임이며 후속 작업이다(CLAUDE.md 8단계 합의). 정렬은 MVP 제외지만 컬럼
헤더 클릭에 대비해 sort_key(레코드→정렬용 값)만 미리 준비해 둔다.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from PySide6.QtCore import Qt


class Col(IntEnum):
    """컬럼 인덱스(모델 columnCount 와 순서의 단일 출처)."""
    NAME = 0
    VOLUME = 1
    TRACK_GAIN = 2
    CLIP = 3
    MAX_AMP = 4


@dataclass(frozen=True)
class ColumnDef:
    """한 컬럼의 정의.

    index    : Col 값(위치).
    header   : 헤더 표기(영문, tr 은 후속).
    align    : 셀 정렬 플래그(Qt.AlignmentFlag).
    sort_key : FileRow 를 받아 정렬용 값을 돌려주는 함수(정렬 MVP 제외, 준비만).
    """
    index: Col
    header: str
    align: Qt.AlignmentFlag
    sort_key: Callable[[object], object]


# 정렬키 헬퍼: 미분석/None 은 정렬 시 가장 뒤로 가도록 보수적 기본값을 준다.
def _num_or_min(value):
    return value if value is not None else float("-inf")


COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef(
        Col.NAME, "Path\\File",
        Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
        lambda row: row.display_name.lower(),
    ),
    ColumnDef(
        Col.VOLUME, "Volume",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        lambda row: _num_or_min(row.get("volume")),
    ),
    ColumnDef(
        Col.TRACK_GAIN, "Track Gain",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        lambda row: _num_or_min(row.get("track_gain_db")),
    ),
    ColumnDef(
        Col.CLIP, "clipping",
        Qt.AlignmentFlag.AlignCenter,
        lambda row: row.clip_state,
    ),
    ColumnDef(
        Col.MAX_AMP, "Curr Max Amp",
        Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter,
        lambda row: _num_or_min(row.get("curr_max_amp")),
    ),
)

COLUMN_COUNT = len(COLUMNS)
