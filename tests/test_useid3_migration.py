"""useId3 분기 통합 테스트 (verify_5c 흡수).

원본 mp3gain 의 useId3 write/read 분기 동작 중, 통합 스위트가 아직 안 덮던
고유 항목을 흡수한다. 라이브러리 함수를 직접 호출한다(mutagen 미사용).

검증(원본 동작 재현):
- APE→ID3 마이그레이션: 먼저 APE 로 게인을 적용해 stale APE 를 만든 뒤,
  use_id3=True 로 다시 적용하면 ID3v2 에 기록되고 stale APE 가 제거된다.
  undo 는 누적된다(APE 적용분 + ID3 적용분).
- read(use_id3=True) 순서: APE 먼저 읽고 ID3 로 덮어쓴다. APE 에 mp3gain
  정보가 있으면 dirty(업그레이드 강제)로 표시된다.
- APE 회귀: use_id3=False 경로는 기존대로 APE 에만 기록(ID3 불변).
- 음수 반환 경로: write_mp3gain_id3_tag 가 파일을 못 열면 음수 반환 →
  _write_mp3gain_tag 는 stale APE 제거를 건너뛰어 예외 없이 통과(원본 >=0 조건).

원본 불간섭(11항목): 모든 작업은 tempfile 사본에서만(BaseGainTest).
"""

from __future__ import annotations

import os
import unittest

from gaindb.tag import (
    read_mp3gain_ape_tag,
    read_mp3gain_tags,
    change_gain_and_tag,
    _write_mp3gain_tag,
    MP3GainTagInfo,
    FileTags,
)
from gaindb.id3 import read_mp3gain_id3_tag, write_mp3gain_id3_tag
from tests._support import BaseGainTest


def _ape_has_mp3gain(path):
    info, _ = read_mp3gain_ape_tag(path)
    return (info.have_track_gain or info.have_album_gain or
            info.have_min_max_gain or info.have_album_min_max_gain or
            info.have_undo)


def _id3_info(path):
    info = MP3GainTagInfo()
    read_mp3gain_id3_tag(path, info)
    return info


class UseId3MigrationTest(BaseGainTest):

    FIXTURE = "test_gain_44k.mp3"

    def test_id3_write_removes_stale_ape(self):
        path = self.copy_fixture(self.FIXTURE)

        # 먼저 APE 로 +3 적용(stale APE 생성).
        info, ft = read_mp3gain_tags(path, use_id3=False)
        change_gain_and_tag(path, 3, 3, info, ft, use_id3=False)
        self.assertTrue(_ape_has_mp3gain(path),
                        "precondition: APE mp3gain must exist")

        # use_id3=True 로 +2 재적용 → ID3 기록 + stale APE 제거.
        info2, ft2 = read_mp3gain_tags(path, use_id3=True)
        change_gain_and_tag(path, 2, 2, info2, ft2, use_id3=True)

        id3 = _id3_info(path)
        self.assertTrue(id3.have_undo, "ID3 must record undo")
        # undo 누적: APE(-3) + ID3(-2) = (-5,-5).
        self.assertEqual((id3.undo_left, id3.undo_right), (-5, -5),
                         "undo must accumulate to (-5,-5)")
        self.assertFalse(_ape_has_mp3gain(path),
                         "stale APE must be removed after ID3 write")

    def test_read_order_and_dirty_upgrade(self):
        path = self.copy_fixture(self.FIXTURE)

        # APE 에만 게인 기록.
        info, ft = read_mp3gain_tags(path, use_id3=False)
        change_gain_and_tag(path, 4, 4, info, ft, use_id3=False)

        # use_id3=True 로 읽으면 APE 값이 읽히고, 업그레이드 강제 dirty.
        info_r, _ = read_mp3gain_tags(path, use_id3=True)
        self.assertTrue(info_r.have_undo, "APE value must be read")
        self.assertTrue(info_r.dirty, "APE->ID3 upgrade must force dirty")

        # ID3 에 다른 undo 를 써서 덮어쓰기 우선순위 확인.
        ov = MP3GainTagInfo()
        ov.have_undo = True
        ov.undo_left = -9
        ov.undo_right = -9
        write_mp3gain_id3_tag(path, ov)

        info_r2, _ = read_mp3gain_tags(path, use_id3=True)
        self.assertEqual((info_r2.undo_left, info_r2.undo_right), (-9, -9),
                         "ID3 value must override APE value")

    def test_ape_regression_use_id3_false(self):
        path = self.copy_fixture(self.FIXTURE)
        info, ft = read_mp3gain_tags(path, use_id3=False)
        change_gain_and_tag(path, 1, 1, info, ft, use_id3=False)
        self.assertTrue(_ape_has_mp3gain(path), "APE must be written")
        self.assertFalse(_id3_info(path).have_undo,
                         "ID3 must be untouched on use_id3=False")

    def test_negative_return_skips_ape_remove(self):
        # 존재하지 않는 파일 → write_mp3gain_id3_tag 음수 반환.
        missing = os.path.join(self._tmpdir, "no_such_file.mp3")
        if os.path.exists(missing):
            os.remove(missing)
        rc = write_mp3gain_id3_tag(missing, MP3GainTagInfo())
        self.assertLess(rc, 0, "missing-file write must return negative")

        # _write_mp3gain_tag 도 음수 경로에서 stale APE 제거를 건너뛰어
        # 예외 없이 통과해야 한다(원본 >=0 조건).
        try:
            _write_mp3gain_tag(missing, MP3GainTagInfo(), FileTags(),
                               use_id3=True)
        except Exception as exc:  # noqa: BLE001 - 실패를 명시적으로 보고
            self.fail(f"_write_mp3gain_tag raised on negative path: {exc!r}")


if __name__ == "__main__":
    unittest.main()
