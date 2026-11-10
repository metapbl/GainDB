# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""-p(파일 날짜 유지) CLI 테스트 (D071).

원본 mp3gain 은 게인을 쓰기 전에 날짜를 저장해 두었다가 쓰기가 끝나면 되돌린다.
게인을 실제로 바꾸는 경로(-r, -a, -g, -u, -s s)마다 날짜가 그대로인지 본다.
오디오가 실제로 바뀌었는지도 함께 확인해 "아무것도 안 해서 통과"를 막는다.
"""

from __future__ import annotations

import os

from tests._support import BaseGainTest

OLD = 1577836800  # 2020-01-01 00:00:00 UTC


class PreserveTimeCliTest(BaseGainTest):
    FIXTURE = "test_gain_44k.mp3"

    def _old_copy(self):
        path = self.copy_fixture(self.FIXTURE)
        os.utime(path, (OLD, OLD))
        return path, self.audio_body_sha256(path)

    def _assert_kept(self, args):
        path, before = self._old_copy()
        r = self.run_cli(args + [path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertNotEqual(self.audio_body_sha256(path), before, msg=args)
        self.assertEqual(int(os.stat(path).st_mtime), OLD, msg=args)

    def test_track(self):
        self._assert_kept(["-r", "-c", "-p"])

    def test_track_skip_tag(self):
        self._assert_kept(["-r", "-c", "-p", "-s", "s"])

    def test_album(self):
        # 파일 하나짜리 -a 는 원본도 바꾸지 않으므로 두 곡으로 앨범을 만든다.
        a, before = self._old_copy()
        b = self.copy_fixture("test_gain_48k.mp3")
        os.utime(b, (OLD, OLD))
        r = self.run_cli(["-a", "-c", "-p", a, b])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertNotEqual(self.audio_body_sha256(a), before)
        self.assertEqual(int(os.stat(a).st_mtime), OLD)
        self.assertEqual(int(os.stat(b).st_mtime), OLD)

    def test_direct_gain(self):
        self._assert_kept(["-g", "2", "-p"])

    def test_undo(self):
        path, _ = self._old_copy()
        self.assertEqual(self.run_cli(["-g", "2", path]).returncode, 0)
        changed = self.audio_body_sha256(path)
        os.utime(path, (OLD, OLD))
        r = self.run_cli(["-u", "-p", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertNotEqual(self.audio_body_sha256(path), changed)
        self.assertEqual(int(os.stat(path).st_mtime), OLD)

    def test_without_p_time_changes(self):
        path, _ = self._old_copy()
        self.assertEqual(self.run_cli(["-g", "2", path]).returncode, 0)
        self.assertNotEqual(int(os.stat(path).st_mtime), OLD)
