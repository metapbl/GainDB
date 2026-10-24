# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""원본 mp3gain CLI 와의 결과 대조 (PRD §1 성공 기준, D038, D049).

같은 fixture 사본 두 벌에 원본 mp3gain 과 gaindb_cli 를 각각 실행해 비교한다.
- `-o -a -c`(분석 + Album 적용): dB 는 0.1dB 이내, peak 는 상대 1e-4 이내,
  나머지(스텝·global gain min/max)는 정확히 같음
- `-s c -o`(적용 뒤 태그): dB 열은 0.1dB 이내, peak 열은 상대 1e-4 이내, 나머지
  열은 정확히 같음
peak 는 디코더(mpglib vs ffmpeg)에 따라 미세하게 다르고, 원본 mp3gain 끼리도 OS
마다 다르다(D049).
- `-u`(undo) 뒤: 오디오 본문 해시가 원본과 같음

mp3gain 이 PATH 에 없으면 건너뛴다(로컬 Windows·CI Windows). CI 의 Ubuntu·macOS
는 mp3gain 설치 단계가 실패하면 작업이 실패하므로 조용히 건너뛰지 않는다.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import unittest
from pathlib import Path

from tests._support import BaseGainTest

MP3GAIN = shutil.which("mp3gain")
FIXTURES = ("test_gain_44k.mp3", "test_stereo_44k.mp3", "test_mono_44k.mp3")
DB_TOL = 0.1
PEAK_REL_TOL = 1e-4


def _table(stdout: str) -> dict[str, list[str]]:
    """-o 탭 출력의 데이터 행을 {파일 이름 또는 "Album": 나머지 열}로."""
    rows = {}
    for line in stdout.splitlines():
        cols = line.split("\t")
        if len(cols) < 6 or cols[0] == "File":
            continue
        key = "Album" if cols[0] == '"Album"' else os.path.basename(cols[0])
        rows[key] = cols[1:]
    return rows


@unittest.skipUnless(MP3GAIN, "mp3gain not on PATH")
class Mp3gainParityTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        self.originals = {}
        self.sides = {"mp3gain": [], "gaindb": []}
        for name in FIXTURES:
            copy = self.copy_fixture(name)
            self.originals[name] = self.audio_body_sha256(copy)
            for side, files in self.sides.items():
                d = Path(self._tmpdir) / side
                d.mkdir(exist_ok=True)
                files.append(shutil.copy2(copy, d / name))

    def _run(self, side: str, *args: str) -> str:
        if side == "mp3gain":
            r = subprocess.run([MP3GAIN, *args, *map(str, self.sides[side])],
                               capture_output=True, text=True, errors="replace")
        else:
            r = self.run_cli([*args, *self.sides[side]])
        self.assertEqual(r.returncode, 0, f"{side} {args}: {r.stderr}")
        return r.stdout

    def _assert_tables_equal(self, args: tuple[str, ...], db_cols: set[int],
                             peak_cols: set[int]) -> None:
        want = _table(self._run("mp3gain", *args))
        got = _table(self._run("gaindb", *args))
        print(f"\n[mp3gain {' '.join(args)}]\n  mp3gain: {want}\n  gaindb:  {got}")
        self.assertEqual(sorted(got), sorted(want))
        for key, cols in want.items():
            self.assertEqual(len(got[key]), len(cols), key)
            for i, (w, g) in enumerate(zip(cols, got[key])):
                with self.subTest(args=args, row=key, col=i):
                    if i in db_cols:
                        self.assertLessEqual(abs(float(g) - float(w)), DB_TOL)
                    elif i in peak_cols:
                        self.assertLessEqual(abs(float(g) - float(w)),
                                             PEAK_REL_TOL * abs(float(w)))
                    else:
                        self.assertEqual(float(g), float(w))

    def test_album_analysis_apply_tags_and_undo_match(self):
        mp3gain_version = subprocess.run([MP3GAIN, "-v"], capture_output=True,
                                         text=True, errors="replace")
        print(f"\nmp3gain version: {(mp3gain_version.stdout + mp3gain_version.stderr).strip()}")

        # 열: MP3 gain, dB gain, Max Amplitude, Max global_gain, Min global_gain
        self._assert_tables_equal(("-o", "-a", "-c"), db_cols={1}, peak_cols={2})
        # 위 5열 + Album gain, Album dB gain, Album Max Amplitude, Album Max/Min global_gain
        self._assert_tables_equal(("-s", "c", "-o"), db_cols={1, 6}, peak_cols={2, 7})

        for side in self.sides:
            self._run(side, "-u")
            for f in self.sides[side]:
                with self.subTest(undo=side, file=f.name):
                    self.assertEqual(self.audio_body_sha256(str(f)),
                                     self.originals[f.name])
