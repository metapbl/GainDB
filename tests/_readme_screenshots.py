# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
r"""README 스크린샷을 샘플 데이터로 생성한다 (readme 표준 §7, D096·D098).

README 이미지는 실제 플랫폼에서 만든다(offscreen 은 글꼴이 없어 글자가 네모로 나온다).

사용: python tests/_readme_screenshots.py <저장 폴더>
합성 fixture 사본을 Music/Album/ 에 넣고, 실제 앱처럼 폴더를 추가해 Album 분석을 마친
주 창을 라이트·다크로 렌더해 main-{light,dark}-v2.png 를 쓴다(화면 캡처 아님).
Windows 에서는 임시 폴더를 빈 드라이브 문자에 subst 로 잠시 연결해, 화면 경로가
`M:\Music\Album\01 Sample.mp3` 꼴이 되고 사용자 이름·임시 폴더가 보이지 않는다.
끝나면 연결을 풀고 임시 폴더를 지운다. 앱 설정은 전용 이름(_SHOT_SETTINGS)을 써서 사용자
설정을 읽거나 건드리지 않는다. 마지막 줄에 결과 JSON 을 쓴다.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QApplication

from tests._support import MP3_DIR

SAMPLES = ("test_gain_44k.mp3", "test_gain_48k.mp3", "test_mono_44k.mp3", "test_stereo_44k.mp3")
# 이미지 내용이 바뀌면 올린다. GitHub 이미지 캐시가 같은 이름의 옛 그림을 계속 보여 준다 (D098).
IMAGE_VERSION = "v3"
_SHOT_SETTINGS = "GaindBReadmeShots"  # 사용자 설정과 분리된 앱 설정 이름


def _mount(folder: str) -> tuple[Path, list[str] | None]:
    """Windows 면 folder 를 빈 드라이브 문자에 연결해 그 루트를, 아니면 folder 를 돌려준다."""
    if sys.platform != "win32":
        return Path(folder), None
    for letter in "MNOPQRSTUVWXYZ":
        drive = f"{letter}:"
        if not os.path.exists(drive + "\\"):
            subprocess.run(["subst", drive, folder], check=True, capture_output=True)
            return Path(drive + "\\"), ["subst", drive, "/d"]
    raise RuntimeError("no free drive letter for subst")


def _wait_idle(app: QApplication, win, timeout: float = 120.0) -> None:
    # 작업이 없어도 0.3초는 이벤트를 돌려 다시 그린 뒤에 찍는다.
    start = time.monotonic()
    while win._is_busy() or time.monotonic() - start < 0.3:
        if time.monotonic() - start > timeout:
            raise TimeoutError("GUI task did not finish")
        app.processEvents()
        time.sleep(0.01)


def render(out_dir: Path) -> dict:
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    tmp = tempfile.mkdtemp(prefix="gaindb_shots_")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope,
                      os.path.join(tmp, "settings"))
    root, unmount = _mount(tmp)
    try:
        return _render(out_dir, root / "Music" / "Album")
    finally:
        if unmount:
            subprocess.run(unmount, check=False, capture_output=True)
        shutil.rmtree(tmp, ignore_errors=True)
        QSettings(_SHOT_SETTINGS, _SHOT_SETTINGS).clear()


def _render(out_dir: Path, album: Path) -> dict:
    album.mkdir(parents=True)
    for i, name in enumerate(SAMPLES, 1):
        shutil.copy2(MP3_DIR / name, album / f"{i:02d} Sample.mp3")

    app = QApplication.instance() or QApplication(sys.argv[:1])
    from gui import theme
    from gui.__main__ import _apply_platform_font
    from gui.i18n import install_translator
    import gui.main_window as mw
    _apply_platform_font(app)  # 실제 앱과 같은 UI 글꼴
    install_translator(app, "en")
    theme.apply_theme(app, "light")
    # QSettings(org, app) 는 기본 형식 설정과 상관없이 레지스트리를 쓴다. 사용자 설정(Maximizing 등)이
    # 화면에 섞이지 않게 빈 전용 이름을 쓰고 끝나면 지운다.
    QSettings(_SHOT_SETTINGS, _SHOT_SETTINGS).clear()
    with mock.patch.object(mw, "resolve_language", return_value="en"), \
            mock.patch.object(mw, "_SETTINGS_ORG", _SHOT_SETTINGS), \
            mock.patch.object(mw, "_SETTINGS_APP", _SHOT_SETTINGS):
        win = mw.MainWindow()
    win.resize(*win._default_window_extent())
    win.show()

    win._add_from([str(album)])  # Add Folder 와 같은 경로
    _wait_idle(app, win)
    win._on_album_analyze()
    _wait_idle(app, win)

    win.table.setFocus()  # 입력칸에 커서가 찍히지 않게
    images = []
    for mode in ("light", "dark"):
        theme.apply_theme(app, mode)
        _wait_idle(app, win, timeout=1.0)
        # Windows 는 창을 띄우거나 테마를 바꿀 때 표·머리글에 시스템 글꼴을 따로 준다. 한국어 Windows(맑은 고딕)면
        # \ 가 ₩ 로 보이므로, README 에는 영문 Windows 와 같게 앱 글꼴을 쓴다(GUI 코드는 그대로).
        for w in (win.table, win.table.horizontalHeader()):
            w.setFont(app.font())
        _wait_idle(app, win, timeout=1.0)
        path = out_dir / f"main-{mode}-{IMAGE_VERSION}.png"
        win.grab().save(str(path))
        images.append(str(path))

    from gui.columns import Col
    model = win.model
    rows = [{"name": model.index(r, Col.NAME).data(),
             "album_volume": model.index(r, Col.ALBUM_VOLUME).data()}
            for r in range(model.rowCount())]
    return {"images": images, "rows": rows, "status": win.statusBar().currentMessage()}


def main() -> int:
    report = render(Path(sys.argv[1]))
    print(json.dumps(report, ensure_ascii=False), flush=True)
    os._exit(0)  # Qt 워커 스레드 정리를 기다리지 않는다 (임시 폴더·드라이브는 render 가 정리)


if __name__ == "__main__":
    sys.exit(main())
