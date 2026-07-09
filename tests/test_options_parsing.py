"""④ 옵션 파싱 단위 테스트 (parse_args 직접 호출, 외부 의존 없음).

원본 mp3gain 의 옵션 체계 재현을 검증한다(verify_cli_ab 의 파싱 부분 이식).
2글자 옵션 인식, 인자 옵션(다음 토큰), -s 서브옵션, -a 가 -r 을 덮음,
붙여쓰기(-g5) 거부→파일 취급, 미인식 옵션 경고 후 계속, 다중 파일.
게인 적용은 하지 않으므로 음원·ffmpeg 불필요(순수 파싱).
"""

from __future__ import annotations

import unittest

from mp3gain_cli import parse_args


def _p(*tail):
    """parse_args(["prog", *tail]) 축약."""
    return parse_args(["prog", *tail])


class OptionParsingUnitTest(unittest.TestCase):

    def test_simple_flags(self):
        o = _p("-r", "-q", "-o", "file.mp3")
        self.assertTrue(o.apply_track and not o.apply_album)
        self.assertTrue(o.quiet_mode)
        self.assertTrue(o.database_format)
        self.assertEqual(o.files, ["file.mp3"])

    def test_a_overrides_r(self):
        # 원본: -r 뒤 -a 면 나중 것(-a)이 이긴다.
        o = _p("-r", "-a", "f.mp3")
        self.assertTrue(o.apply_album and not o.apply_track)

    def test_temp_flags_case_sensitive(self):
        self.assertFalse(_p("-T", "f.mp3").using_temp)  # 대문자 T → 직접 수정
        self.assertTrue(_p("-t", "f.mp3").using_temp)   # 소문자 t → 임시파일

    def test_arg_options_take_next_token(self):
        o = _p("-g", "5", "f.mp3")
        self.assertTrue(o.direct_gain and o.direct_gain_val == 5)
        self.assertEqual(o.files, ["f.mp3"])

        self.assertEqual(_p("-g", "-3", "f.mp3").direct_gain_val, -3)

        self.assertAlmostEqual(_p("-d", "1.5", "f.mp3").db_gain_mod, 1.5)
        self.assertEqual(_p("-m", "2", "f.mp3").mp3_gain_mod, 2)

    def test_l_takes_two_args(self):
        o = _p("-l", "1", "4", "f.mp3")
        self.assertTrue(o.direct_single_channel_gain)
        self.assertEqual(o.which_channel, 1)
        self.assertEqual(o.direct_gain_val, 4)
        self.assertEqual(o.files, ["f.mp3"])

    def test_s_suboptions(self):
        self.assertTrue(_p("-s", "i", "f.mp3").use_id3)
        self.assertFalse(_p("-s", "a", "f.mp3").use_id3)
        self.assertTrue(_p("-s", "c", "f.mp3").check_tag_only)
        self.assertTrue(_p("-s", "s", "f.mp3").skip_tag)
        self.assertTrue(_p("-s", "r", "f.mp3").force_recalculate_tag)
        self.assertTrue(_p("-s", "u", "f.mp3").force_update_tag)
        self.assertTrue(_p("-s", "d", "f.mp3").delete_tag)

    def test_glued_arg_rejected_as_option(self):
        # -g5 는 2글자 옵션이 아니므로 옵션이 아니라 파일명으로 취급된다(합의 예외).
        o = _p("-g5", "f.mp3")
        self.assertFalse(o.direct_gain)
        self.assertEqual(o.files, ["-g5", "f.mp3"])

    def test_unrecognized_option_warns_and_continues(self):
        # 미인식 2글자 옵션은 경고만 하고 계속(원본 동작). 파일은 정상 수집.
        o = _p("-z", "f.mp3")
        self.assertEqual(o.files, ["f.mp3"])

    def test_multiple_files(self):
        o = _p("-a", "a.mp3", "b.mp3", "c.mp3")
        self.assertEqual(o.files, ["a.mp3", "b.mp3", "c.mp3"])


if __name__ == "__main__":
    unittest.main()
