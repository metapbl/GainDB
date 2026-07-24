# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""gui/resources.py — 리소스(아이콘 등) 경로 해석 헬퍼.

개발 실행(python -m gui)과 PyInstaller 번들(onefile/onedir) 양쪽에서 동일하게
리소스를 찾도록 기준 경로를 결정한다. PyInstaller 는 번들 시 데이터를 임시
폴더에 풀고 그 경로를 sys._MEIPASS 에 넣으므로, 그 값이 있으면 그것을,
없으면 리포지토리 루트(이 파일의 상위 폴더)를 기준으로 삼는다.

아이콘 파일이 없어도 앱이 죽지 않도록 app_icon() 은 파일이 없으면 빈 QIcon 을
돌려준다(트레이/창 아이콘이 비어 보일 뿐 기능은 유지).
"""

from __future__ import annotations

import os
import sys

from PySide6.QtGui import QIcon


def _base_dir() -> str:
    """리소스 탐색 기준 폴더. PyInstaller 면 _MEIPASS/gui, 아니면 이 파일(gui) 폴더.

    아이콘·번역본은 gui 패키지 안에 두어(assets/·translations/) 소스 실행과
    wheel/pip 설치본 양쪽에서 동일하게 찾히도록 한다. i18n.py 의 _base_dir 과
    같은 패턴(gui 기준)이다.
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return os.path.join(str(meipass), "gui")
    # 이 파일: <root>/gui/resources.py -> 이 파일이 있는 gui 폴더가 기준.
    return os.path.dirname(os.path.abspath(__file__))


def resource_path(*parts: str) -> str:
    """기준 폴더 아래의 리소스 절대경로를 만든다(존재 보장 없음)."""
    return os.path.join(_base_dir(), *parts)


# 앱 아이콘 파일 경로(gui/assets/GainDB.png). 창 아이콘·트레이 아이콘 공용.
APP_ICON_PATH = resource_path("assets", "GainDB.png")


def app_icon() -> QIcon:
    """앱 아이콘 QIcon. 파일이 없으면 빈 QIcon(앱은 계속 동작)."""
    if os.path.exists(APP_ICON_PATH):
        return QIcon(APP_ICON_PATH)
    return QIcon()
