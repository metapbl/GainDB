# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""GUI Album 워커 ↔ CLI 대조 (PRD F5 마지막 인수 기준, D038).

GUI 의 Album 분석·적용·undo 워커를 offscreen 에서 같은 스레드로 run() 해
같은 fixture 의 다른 사본에 CLI `-a -c` 를 적용한 결과와 비교한다.
- GUI 가 적용한 스텝 == CLI Album 스텝
- 적용 뒤 `-s c -o` 태그 표가 두 사본에서 같음
- GUI 쪽 undo 뒤 오디오 본문 해시가 원본과 같음
CLI 가 원본 mp3gain 과 같다는 것은 test_mp3gain_parity 가 맡는다.
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from tests._support import BaseGainTest
from tests.test_mp3gain_parity import FIXTURES, _table


class GuiAlbumParityTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
        from PySide6.QtWidgets import QApplication
        QApplication.instance() or QApplication([])

        self.originals = {}
        self.sides = {"gui": [], "cli": []}
        for name in FIXTURES:
            copy = self.copy_fixture(name)
            self.originals[name] = self.audio_body_sha256(copy)
            for side, files in self.sides.items():
                d = Path(self._tmpdir) / side
                d.mkdir(exist_ok=True)
                files.append(str(shutil.copy2(copy, d / name)))

    def test_album_apply_and_undo_match_cli(self):
        from gaindb.api import DEFAULT_TARGET_DB, group_by_album
        from gui.workers import AlbumAnalyzeWorker, AlbumApplyWorker, FileActionWorker

        gui_files = self.sides["gui"]
        groups = group_by_album(gui_files, each_folder_is_album=False)
        failed = []

        analyze = AlbumAnalyzeWorker(groups, DEFAULT_TARGET_DB)
        seeds = {}
        analyze.row_raw.connect(lambda p, raw: seeds.__setitem__(p, raw))
        analyze.failed.connect(lambda p, msg: failed.append((p, msg)))
        analyze.run()
        self.assertEqual(sorted(seeds), sorted(gui_files))

        apply = AlbumApplyWorker(groups, DEFAULT_TARGET_DB, seeds)
        applied = {}
        apply.row_applied.connect(lambda p, shown, steps: applied.__setitem__(p, steps))
        apply.failed.connect(lambda p, msg: failed.append((p, msg)))
        apply.run()
        self.assertEqual(failed, [])

        r = self.run_cli(["-o", "-a", "-c", *self.sides["cli"]])
        self.assertEqual(r.returncode, 0, r.stderr)
        album_steps = int(_table(r.stdout)["Album"][0])
        self.assertNotEqual(album_steps, 0)  # 적용이 실제로 일어나는 fixture 여야 의미가 있다
        self.assertEqual({os.path.basename(p): s for p, s in applied.items()},
                         {name: album_steps for name in FIXTURES})

        tags = {}
        for side, files in self.sides.items():
            r = self.run_cli(["-s", "c", "-o", *files])
            self.assertEqual(r.returncode, 0, r.stderr)
            tags[side] = _table(r.stdout)
        self.assertEqual(tags["gui"], tags["cli"])

        undo = FileActionWorker(gui_files, "undo")
        undo.failed.connect(lambda p, msg: failed.append((p, msg)))
        undo.run()
        self.assertEqual(failed, [])
        for f in gui_files:
            with self.subTest(file=os.path.basename(f)):
                self.assertEqual(self.audio_body_sha256(f),
                                 self.originals[os.path.basename(f)])
