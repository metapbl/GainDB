# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""공통 인프라 자체 점검(smoke).

인프라가 실제로 동작하는지만 확인한다: CLI 헬퍼가 -v 를 실행하는지,
음원이 있으면 사본 생성·정리·본문 해시가 동작하고 원본 가드가 작동하는지.
음원이 없으면 해당 테스트는 자동 skip.
"""

from __future__ import annotations

import os
import unittest
from pathlib import Path

from tests._support import (
    BaseGainTest,
    KNOWN_FIXTURES,
    available_fixtures,
    fixture_path,
)


class SupportSmokeTest(BaseGainTest):

    def test_cli_version_runs(self):
        # -v 는 음원 없이도 동작해야 한다(배너/버전 출력).
        result = self.run_cli(["-v"])
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        combined = (result.stdout or "") + (result.stderr or "")
        self.assertTrue(combined.strip(), "version output was empty")

    def test_copy_fixture_and_body_hash(self):
        avail = available_fixtures()
        if not avail:
            self.skipTest("no test fixtures available")
        name = avail[0].name
        copy = self.copy_fixture(name)

        # 사본은 tempdir 안에 있어야 하고 원본 경로와 달라야 한다.
        self.assertTrue(Path(copy).is_file())
        self.assertNotEqual(Path(copy).resolve(), fixture_path(name).resolve())

        # 본문 해시가 계산되고, 같은 파일에 대해 안정적이어야 한다.
        h1 = self.audio_body_sha256(copy)
        h2 = self.audio_body_sha256(copy)
        self.assertEqual(h1, h2)
        self.assertEqual(len(h1), 64)

    def test_guard_detects_modification(self):
        # 원본 가드가 실제로 변경을 잡는지 직접 확인(원본은 건드리지 않음).
        avail = available_fixtures()
        if not avail:
            self.skipTest("no test fixtures available")
        # 사본을 하나 만들어 가드에 임시 등록·변경 후 verify 가 실패하는지 본다.
        from tests._support import FixtureGuard
        copy = Path(self.copy_fixture(avail[0].name))
        guard = FixtureGuard()
        guard._hashes[copy] = "0" * 64  # 일부러 틀린 해시
        with self.assertRaises(AssertionError):
            guard.verify()


if __name__ == "__main__":
    unittest.main()
