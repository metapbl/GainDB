# SPDX-License-Identifier: LGPL-2.1-or-later
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""README 6개 언어(D080·D081)와 GUI ffmpeg 안내 링크(D088)가 실제 파일·절을 가리킨다."""

from __future__ import annotations

import os
import re
import unittest
from urllib.parse import unquote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_URL = "https://github.com/metapbl/GainDB/blob/main/"


def readme_name(lang: str) -> str:
    """GUI 언어 코드 → README 파일 이름 (en 은 README.md, zh_CN 은 README.zh-CN.md)."""
    return "README.md" if lang == "en" else f"README.{lang.replace('_', '-')}.md"


def read(name: str) -> str:
    with open(os.path.join(ROOT, name), encoding="utf-8") as f:
        return f.read()


def anchors(text: str) -> set[str]:
    """GitHub 식 제목 앵커: 소문자, 글자·숫자·공백·-·_ 만 남기고 공백은 -."""
    text = re.sub(r"```.*?```", "", text, flags=re.S)  # 코드 블록 안 '#' 줄은 제목이 아니다
    out = set()
    for m in re.finditer(r"^#{1,6} (.+)$", text, flags=re.M):
        out.add(re.sub(r"[^\w\- ]", "", m.group(1).strip().lower()).replace(" ", "-"))
    return out


def h2_count(text: str) -> int:
    return len(re.findall(r"^## ", re.sub(r"```.*?```", "", text, flags=re.S), flags=re.M))


class ReadmeTest(unittest.TestCase):
    def setUp(self) -> None:
        from gui.i18n import LANGUAGES
        from gui.main_window import _FFMPEG_HELP_URL
        self.langs = LANGUAGES
        self.urls = _FFMPEG_HELP_URL

    def test_ffmpeg_link_points_to_section_of_language_readme(self):
        self.assertEqual(set(self.urls), set(self.langs))
        for lang in self.langs:
            with self.subTest(lang=lang):
                url = self.urls[lang]
                self.assertTrue(url.startswith(REPO_URL), url)
                name, _, anchor = url[len(REPO_URL):].partition("#")
                self.assertEqual(name, readme_name(lang))
                self.assertIn(unquote(anchor), anchors(read(name)))

    def test_language_line_files_exist_and_match_english(self):
        en = read("README.md")
        names = [readme_name(lang) for lang in self.langs]
        badges = len(re.findall(r"img\.shields\.io", en))
        self.assertEqual(badges, 4)
        for name in names:
            with self.subTest(readme=name):
                text = read(name)
                for target in names:
                    self.assertIn(f'href="{target}"', text)
                self.assertEqual(h2_count(text), h2_count(en))
                self.assertEqual(len(re.findall(r"img\.shields\.io", text)), badges)

    def test_relative_links_exist(self):
        for lang in self.langs:
            name = readme_name(lang)
            text = read(name)
            own = anchors(text)
            for target in re.findall(r'(?:\]\(|href=")([^)"]+)', text):
                if target.startswith(("http://", "https://")):
                    continue
                with self.subTest(readme=name, link=target):
                    path, _, frag = target.partition("#")
                    if path:
                        self.assertTrue(os.path.exists(os.path.join(ROOT, path)), target)
                    else:
                        self.assertIn(unquote(frag), own)


if __name__ == "__main__":
    unittest.main()
