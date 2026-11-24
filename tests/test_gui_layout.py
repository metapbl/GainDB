# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""창 폭·머리글·선택·언어 테스트 (F11, D111~D115)."""

from __future__ import annotations

import unittest


class WrapHeaderTest(unittest.TestCase):
    """머리글 두 줄 규칙(D115). 폭은 글자 수로 재서 글꼴과 무관하게 본다."""

    def wrap(self, text):
        from gui.columns import wrap_header
        return wrap_header(text, len)

    def test_splits_at_space_and_before_parenthesis(self):
        self.assertEqual(self.wrap("Track Gain"), ("Track\nGain", 5))
        self.assertEqual(self.wrap("clip(Album)"), ("clip\n(Album)", 7))
        self.assertEqual(self.wrap("클립(앨범)"), ("클립\n(앨범)", 4))
        self.assertEqual(self.wrap("앨범 볼륨"), ("앨범\n볼륨", 2))

    def test_never_inside_hangul_or_latin_word(self):
        for word in ("볼륨", "클리핑", "Volume", "clipping", "saturación"):
            with self.subTest(word=word):
                self.assertEqual(self.wrap(word), (word, len(word)))

    def test_japanese_splits_only_where_script_changes(self):
        self.assertEqual(self.wrap("トラックゲイン"), ("トラックゲイン", 7))
        self.assertEqual(self.wrap("アルバム音量"), ("アルバム\n音量", 4))
        self.assertEqual(self.wrap("現在の最大振幅"), ("現在の\n最大振幅", 4))

    def test_chinese_splits_every_two_han(self):
        self.assertEqual(self.wrap("音轨增益"), ("音轨\n增益", 2))
        self.assertEqual(self.wrap("当前最大振幅"), ("当前\n最大振幅", 4))
        self.assertEqual(self.wrap("削波"), ("削波", 2))
        self.assertEqual(self.wrap("削波(专辑)"), ("削波\n(专辑)", 4))
