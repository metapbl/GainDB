# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""실제 플랫폼에서 GUI 흐름을 돌리고 캡처한다 (macOS 러너 검증, D063).

사용: python tests/_gui_capture.py <저장 폴더>
임시 사본에 파일 추가 → Album 분석 → Album 적용 → undo 를 돌리고 단계마다 주 창을
PNG 로 저장한다. undo 뒤 오디오 해시가 다르면 종료 코드 1, 시간 초과는 2.
QSettings 도 임시 INI 라 사용자 설정과 fixture 원본을 건드리지 않는다.
"""

from __future__ import annotations

import glob
import importlib.util
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import QEvent, QSettings, Qt, QTimer
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import QApplication

from tests._support import MP3_DIR, BaseGainTest

FIXTURES = ("test_gain_44k.mp3", "test_gain_48k.mp3", "test_mono_44k.mp3")


def main() -> int:
    out = Path(sys.argv[1]).resolve()
    out.mkdir(parents=True, exist_ok=True)

    tmp = tempfile.mkdtemp(prefix="gaindb_capture_")
    QSettings.setDefaultFormat(QSettings.Format.IniFormat)
    QSettings.setPath(QSettings.Format.IniFormat, QSettings.Scope.UserScope, tmp)
    album = Path(tmp) / "Album"
    album.mkdir()
    for name in FIXTURES:
        shutil.copy2(MP3_DIR / name, album / name)
    (album / "broken.mp3").write_bytes(b"not an mp3" * 50)
    good = [str(album / name) for name in FIXTURES]
    hash_of = BaseGainTest().audio_body_sha256
    before = {p: hash_of(p) for p in good}

    app = QApplication(sys.argv[:1])
    print("platform:", app.platformName(), flush=True)

    from gui.main_window import MainWindow
    win = MainWindow()
    win.resize(1040, 480)
    win.show()

    def shot(name: str) -> None:
        win.grab().save(str(out / f"{name}.png"))

    def screen(name: str) -> None:
        # 네이티브 메뉴바까지 찍히는 화면 전체 캡처. 러너 권한에 따라 실패할 수 있다.
        if sys.platform == "darwin":
            r = subprocess.run(["screencapture", "-x", str(out / f"{name}.png")], check=False)
            print(f"screencapture {name}: exit {r.returncode}", flush=True)

    def finish(code: int) -> None:
        print("app name:", app.applicationName(), flush=True)
        print("add files tooltip:", win.act_add_files.toolTip(), flush=True)
        os._exit(code)

    def key_test() -> None:
        win.table.selectRow(0)
        rows = win.model.rowCount()
        event = QKeyEvent(QEvent.Type.KeyPress, Qt.Key.Key_Backspace,
                          Qt.KeyboardModifier.NoModifier)
        QApplication.sendEvent(win.table, event)
        print(f"backspace rows: {rows} -> {win.model.rowCount()}", flush=True)

    def themes() -> None:
        if importlib.util.find_spec("gui.theme") is None:
            return
        from gui import theme
        for mode in ("dark", "light"):
            theme.apply_theme(app, mode)
            app.processEvents()
            shot(f"theme_{mode}")
            screen(f"screen_{mode}")

    state = {"step": 0}

    def step() -> None:
        if win._is_busy():
            return
        state["step"] += 1
        status = win.statusBar().currentMessage()
        print(f"step {state['step']}: {status}", flush=True)
        if state["step"] == 1:
            shot("1_added")
            screen("screen_added")
            win._on_album_analyze()
        elif state["step"] == 2:
            shot("2_analyzed")
            # 깨진 파일이 앨범에 있으면 Album 적용이 통째로 멈추므로 뺀다 (O32).
            win.model.remove_rows([win.model.find_row_by_path(str(album / "broken.mp3"))])
            win._on_album_gain()
        elif state["step"] == 3:
            shot("3_applied")
            win.table.selectAll()
            win._on_ctx_undo()
        else:
            shot("4_undone")
            changed = [p for p in good if hash_of(p) != before[p]]
            print("audio changed after undo:", changed, flush=True)
            themes()
            key_test()
            finish(1 if changed else 0)

    win._add_from([str(album)])
    timer = QTimer()
    timer.timeout.connect(step)
    timer.start(500)
    QTimer.singleShot(300000, lambda: finish(2))
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
