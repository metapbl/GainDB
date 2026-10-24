# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""F6 ffmpeg 찾기 테스트.

PATH 를 빈 임시 폴더로 바꿔 ffmpeg/ffprobe 가 없는 환경을 흉내 낸다.
fixture 는 BaseGainTest 의 tempfile 사본에서만 다룬다.
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest import mock

from gaindb.decode import DecodeError, decode_pcm
from tests._support import BaseGainTest, _sha256


class NoFfmpegTest(BaseGainTest):
    def setUp(self) -> None:
        super().setUp()
        self._empty = tempfile.mkdtemp(prefix="gaindb_nopath_", dir=self._tmpdir)
        patcher = mock.patch.dict(os.environ, {"PATH": self._empty})
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_decode_raises_and_leaves_file_unchanged(self):
        copy = self.copy_fixture("test_gain_44k.mp3")
        before = _sha256(Path(copy))
        with self.assertRaises(DecodeError):
            decode_pcm(Path(copy))
        self.assertEqual(_sha256(Path(copy)), before)
