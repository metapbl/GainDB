# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""255/0 클램프 비가역성 단위 테스트 (fixture·ffmpeg 불필요, 항상 실행).

writer._apply_one 은 global_gain(8bit, 0~255)에 change 를 더하되 상·하한을
클램프한다(mp3gain 과 동일한 동작). 클램프가 일어나면 초과분이 소실되어
+N 후 -N(undo)을 해도 원래 값으로 못 돌아온다(비가역). 이 성질을 값 단위로
직접 검증한다.

배경: 통합 round-trip 테스트는 안전한 방향(음수 스텝 먼저)으로만 왕복하므로
클램프 경로를 일부러 피한다. 또 합성 fixture 의 max global_gain 은 인코더
특성상 255 에 못 미칠 수 있어(현재 44.1k 계열 max=210) 클램프 경계를 자연히
타지 않는다. 따라서 클램프 비가역성은 fixture 에 맡기지 않고 여기서 코드로
확정한다(9항 '0-gain·255-gain 프레임은 클램프로 비가역' 영구 제약의 회귀 고정).
"""

from __future__ import annotations

import unittest

from gaindb.writer import _apply_one


class ApplyOneClampTest(unittest.TestCase):
    """_apply_one 의 상·하한 클램프와 0-gain 불변(wrap=False)."""

    def test_upper_clamp_at_255(self):
        # 255 초과는 255 로 잘린다.
        self.assertEqual(_apply_one(255, 10, False), 255)
        self.assertEqual(_apply_one(250, 20, False), 255)
        # 정확히 255 도달은 클램프 아님(초과분 없음).
        self.assertEqual(_apply_one(245, 10, False), 255)
        self.assertEqual(_apply_one(200, 55, False), 255)

    def test_lower_clamp_at_0(self):
        # 0 미만은 0 으로 잘린다(단, 시작값이 0 이 아닐 때).
        self.assertEqual(_apply_one(5, -10, False), 0)
        self.assertEqual(_apply_one(200, -255, False), 0)

    def test_zero_gain_frame_unchanged(self):
        # gain==0 프레임은 change 와 무관하게 0 을 유지한다(건드리지 않음).
        self.assertEqual(_apply_one(0, 10, False), 0)
        self.assertEqual(_apply_one(0, -10, False), 0)
        self.assertEqual(_apply_one(0, 0, False), 0)

    def test_no_clamp_in_range(self):
        # 경계에서 먼 값은 그대로 산술 적용된다.
        self.assertEqual(_apply_one(200, 10, False), 210)
        self.assertEqual(_apply_one(200, -10, False), 190)
        self.assertEqual(_apply_one(128, 0, False), 128)


class ApplyOneReversibilityTest(unittest.TestCase):
    """+N 후 -N 왕복의 가역/비가역 판정(무손실 조정의 핵심 제약)."""

    def test_reversible_when_no_clamp(self):
        # 상·하한에서 먼 값은 +N → -N 이 정확히 복원된다(가역).
        for gain in (100, 150, 200):
            for n in (1, 3, 10):
                with self.subTest(gain=gain, n=n):
                    up = _apply_one(gain, n, False)
                    back = _apply_one(up, -n, False)
                    self.assertEqual(back, gain,
                                     "in-range gain must round-trip exactly")

    def test_irreversible_on_upper_clamp(self):
        # 255 상한을 넘겨 클램프되면 undo 로 원값 복원 불가(비가역).
        gain = 250
        up = _apply_one(gain, 10, False)      # 260 -> 255 (클램프, 5 소실)
        self.assertEqual(up, 255)
        back = _apply_one(up, -10, False)     # 255 - 10 = 245 != 250
        self.assertEqual(back, 245)
        self.assertNotEqual(back, gain,
                            "clamped upper gain must NOT round-trip")

    def test_irreversible_on_lower_clamp(self):
        # 0 하한 아래로 내려가 클램프되면 undo 로 복원 불가(비가역).
        gain = 5
        down = _apply_one(gain, -10, False)   # -5 -> 0 (클램프, 5 소실)
        self.assertEqual(down, 0)
        # gain==0 이 되었으므로 이후 +N 은 0-gain 불변 규칙에 걸려 0 유지.
        back = _apply_one(down, 10, False)    # 0 프레임은 안 건드림 -> 0
        self.assertEqual(back, 0)
        self.assertNotEqual(back, gain,
                            "clamped lower gain must NOT round-trip")


class ApplyOneWrapTest(unittest.TestCase):
    """wrap=True 는 클램프가 아니라 8bit 순환(& 0xFF). 별개 모드."""

    def test_wrap_wraps_around_not_clamp(self):
        # wrap 은 상·하한 클램프도 0-gain 예외도 적용하지 않고 순환한다.
        self.assertEqual(_apply_one(255, 1, True), 0)      # 256 & 0xFF
        self.assertEqual(_apply_one(0, -1, True), 255)     # -1 & 0xFF
        self.assertEqual(_apply_one(0, 10, True), 10)      # 0-gain 예외 없음
        self.assertEqual(_apply_one(200, 100, True), 44)   # 300 & 0xFF

    def test_wrap_is_reversible(self):
        # 순환은 정보 손실이 없어 +N -> -N 이 언제나 가역이다(클램프와 대비).
        for gain in (0, 5, 250, 255):
            for n in (1, 10, 100):
                with self.subTest(gain=gain, n=n):
                    up = _apply_one(gain, n, True)
                    back = _apply_one(up, -n, True)
                    self.assertEqual(back, gain,
                                     "wrap mode must always round-trip")


if __name__ == "__main__":
    unittest.main()