r"""gui/columns.py — 리스트뷰 컬럼 정의(상수 테이블).

메인 창의 컬럼 구성을 관찰해 정의한다. MVP 는 Track 묶음(Volume / Track Gain /
clipping)에 더해 Album 묶음(Album Volume / Album Gain / clip(Album))을
mp3gain 과 동일한 순서로 노출한다:
  Path\File / Volume / Track Gain / clipping /
  Album Volume / Album Gain / clip(Album) / Curr Max Amp
(clip(Track)·Max Noclip 은 MVP 제외 — CLAUDE.md 참조. 컬럼 순서상 Track 묶음
뒤에 Album 묶음, 맨 끝이 Curr Max Amp.)

헤더 문자열은 mp3gain 과 동일한 영문 표기 그대로 둔다. 다국어화는 GUI 계층의
tr() 책임이며 후속 작업이다(CLAUDE.md 8단계 합의). 정렬·표시 배선은 model 의
_display_text/_sort_value 가 담당하므로 sort_key 필드는 현재 쓰이지 않으나,
ColumnDef 시그니처 유지를 위해 채워 둔다.

default_width: 컬럼 초기폭(px). 최초 실행(저장된 폭 없음)과 "Reset Column
Widths"에서 이 값으로 되돌린다. 전 컬럼이 Interactive(사용자 드래그로 개별
조절, 넘치면 가로 스크롤)라 NAME 도 이 폭이 실제 초기값이 된다(Path\File 은
넉넉히 480).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum
from typing import Callable

from PySide6.QtCore import Qt, QT_TRANSLATE_NOOP


class Col(IntEnum):
    """컬럼 인덱스(모델 columnCount 와 순서의 단일 출처).

    컬럼 순서: Track 묶음 → Album 묶음 → Curr Max Amp.
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

    index         : Col 값(위치).
    header        : 헤더 표기(영문, tr 은 후속).
    align         : 셀 정렬 플래그(Qt.AlignmentFlag).
    default_width : 초기폭(px). 최초 실행·Reset 시 적용.
    sort_key      : FileRow 를 받아 정렬용 값을 돌려주는 함수(현재 미사용, 준비만).
    """
    index: Col
    header: str
    align: Qt.AlignmentFlag
    default_width: int
    sort_key: Callable[[object], object]


# 정렬키 헬퍼(현재 미사용): 미분석/None 은 뒤로 가도록 보수적 기본값.
def _num_or_min(value):
    return value if value is not None else float("-inf")


_RIGHT = Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter
_LEFT = Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter
_CENTER = Qt.AlignmentFlag.AlignCenter


COLUMNS: tuple[ColumnDef, ...] = (
    ColumnDef(Col.NAME, QT_TRANSLATE_NOOP("FileTableModel", "Path\\File"), _LEFT, 480,
              lambda row: str(getattr(row, "path", "")).lower()),
    ColumnDef(Col.VOLUME, QT_TRANSLATE_NOOP("FileTableModel", "Volume"), _RIGHT, 80,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.TRACK_GAIN, QT_TRANSLATE_NOOP("FileTableModel", "Track Gain"), _RIGHT, 90,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.CLIP, QT_TRANSLATE_NOOP("FileTableModel", "clipping"), _CENTER, 70,
              lambda row: ""),
    ColumnDef(Col.ALBUM_VOLUME, QT_TRANSLATE_NOOP("FileTableModel", "Album Volume"), _RIGHT, 100,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.ALBUM_GAIN, QT_TRANSLATE_NOOP("FileTableModel", "Album Gain"), _RIGHT, 90,
              lambda row: _num_or_min(None)),
    ColumnDef(Col.ALBUM_CLIP, QT_TRANSLATE_NOOP("FileTableModel", "clip(Album)"), _CENTER, 80,
              lambda row: ""),
    ColumnDef(Col.MAX_AMP, QT_TRANSLATE_NOOP("FileTableModel", "Curr Max Amp"), _RIGHT, 110,
              lambda row: _num_or_min(None)),
)

COLUMN_COUNT = len(COLUMNS)