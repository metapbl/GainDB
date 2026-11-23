# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""README 스크린샷 생성 스크립트(D096·D098·D099): 라이트·다크 PNG, 실제 앱 같은 경로에 로컬 정보 없음.

테마·작업 폴더·QSettings 형식은 프로세스 전체에 걸리므로 스크립트를 하위 프로세스로 돌린다.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tests._support import REPO_ROOT, fixture_path

SCRIPT = REPO_ROOT / "tests" / "_readme_screenshots.py"
MAX_BYTES = 2 * 1024 * 1024


class ReadmeScreenshotsTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        fixture_path("test_gain_44k.mp3")  # fixture 가 없으면 건너뛴다
        cls._tmp = tempfile.TemporaryDirectory(prefix="gaindb_shots_test_")
        cls.out = Path(cls._tmp.name)
        env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
        r = subprocess.run([sys.executable, str(SCRIPT), str(cls.out)], env=env,
                           capture_output=True, text=True, encoding="utf-8", timeout=300)
        if r.returncode != 0:
            raise AssertionError(f"script failed ({r.returncode}):\n{r.stdout}\n{r.stderr}")
        cls.report = json.loads(r.stdout.strip().splitlines()[-1])

    @classmethod
    def tearDownClass(cls) -> None:
        cls._tmp.cleanup()

    def test_render_writes_light_and_dark(self):
        from PySide6.QtGui import QImage
        names = [Path(p).name for p in self.report["images"]]
        self.assertEqual(names, ["main-light-v2.png", "main-dark-v2.png"])
        for name in names:
            with self.subTest(image=name):
                path = self.out / name
                self.assertTrue(path.is_file())
                self.assertLessEqual(path.stat().st_size, MAX_BYTES)
                img = QImage(str(path))
                self.assertFalse(img.isNull())
                self.assertGreater(img.width() * img.height(), 0)

    @unittest.skipUnless(sys.platform == "win32", "README 이미지는 Windows 에서 만든다 (subst)")
    def test_rows_show_real_path_without_local_info(self):
        rows = self.report["rows"]
        self.assertEqual(len(rows), 4)
        user = Path(os.path.expanduser("~")).name.lower()
        temp = tempfile.gettempdir().lower()
        for row in rows:
            with self.subTest(row=row["name"]):
                # 실제 앱처럼 절대 경로를 보이되, 연결한 드라이브라 사용자·임시 폴더가 없다.
                self.assertRegex(row["name"], r"^[M-Z]:\\Music\\Album\\0[1-4] Sample\.mp3$")
                self.assertNotIn(user, row["name"].lower())
                self.assertNotIn(temp, row["name"].lower())
                self.assertTrue(row["album_volume"], "Album 분석 결과가 없다")

    @unittest.skipUnless(sys.platform == "win32", "subst 는 Windows 전용")
    def test_drive_mapping_is_removed(self):
        import subprocess
        letters = {row["name"][:2] for row in self.report["rows"]}
        mapped = subprocess.run(["subst"], capture_output=True, text=True).stdout
        for drive in letters:
            self.assertNotIn(drive, mapped)
            self.assertFalse(os.path.exists(drive + "\\"))


if __name__ == "__main__":
    unittest.main()
