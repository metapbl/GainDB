# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""GUI 순수 함수부 테스트(원본 음원·ffmpeg 불필요, 항상 실행).

대상(8단계 (b) 편입):
  - collect_mp3_paths (main_window): 파일/폴더 → .mp3 경로 수집·recurse.
  - FileTableModel._index 불변식 (model): add/remove/clear 후 path→row 일관성,
    find_row_by_path O(1) 조회 정확성(perf 커밋의 안전망).
  - recompute_target (api): 목표 변경 시 재표시. 비파괴·no_tag 처리·수식.
  - shift_after_apply (api): 적용 후 재표시. steps 0 수렴·peak 이동·비파괴.

이 넷은 디코딩·원본 음원이 전혀 필요 없으므로 BaseGainTest(FixtureGuard/
tempdir)를 상속하지 않고 unittest.TestCase 를 직접 쓴다. collect_mp3_paths
테스트만 빈 .mp3 파일을 만들 자체 tempdir 를 tempfile.TemporaryDirectory 로
자족한다(내용을 파싱하지 않으므로 빈 파일이면 충분).

PySide6 미설치 환경에서는 모듈 로드가 실패하므로 상단에서 통째로 SkipTest
한다. FileTableModel 은 QObject(위젯 아님)라 QApplication 없이 인스턴스화되나,
안전을 위해 모듈 로드 시 QCoreApplication 이 없으면 하나 만들어 둔다.
"""

from __future__ import annotations

import os
import tempfile
import unittest

# PySide6/gui 의존은 있을 때만. 없으면 이 모듈 전체를 건너뛴다.
try:
    from PySide6.QtCore import QCoreApplication
    from gui.main_window import collect_mp3_paths
    from gui.model import FileTableModel
    from gaindb.api import (
        recompute_target,
        shift_after_apply,
        DEFAULT_TARGET_DB,
    )
    from gaindb.analysis import DB_PER_STEP
    _HAVE_GUI = True

    # QObject 계열 인스턴스화를 위해 애플리케이션 객체를 한 번 확보한다
    # (위젯이 아니라 필수는 아니지만, Qt 초기화 경고를 피하기 위한 안전장치).
    if QCoreApplication.instance() is None:
        _app = QCoreApplication([])
except Exception as _exc:  # noqa: BLE001 - import 실패 사유를 skip 메시지로
    _HAVE_GUI = False
    _IMPORT_ERROR = _exc


@unittest.skipUnless(_HAVE_GUI, "PySide6/gui not importable")
class TestCollectMp3Paths(unittest.TestCase):
    """collect_mp3_paths: 파일/폴더에서 .mp3 만 절대경로로 수집한다."""

    def setUp(self) -> None:
        self._td = tempfile.TemporaryDirectory(prefix="gaindb_collect_")
        self.root = self._td.name

    def tearDown(self) -> None:
        self._td.cleanup()

    def _touch(self, *parts: str) -> str:
        """root 하위에 빈 파일을 만들고 절대경로를 반환(중간 폴더 자동 생성)."""
        p = os.path.join(self.root, *parts)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, "wb"):
            pass
        return os.path.abspath(p)

    def test_file_arg_only_mp3(self):
        """파일 인자는 .mp3 일 때만 포함, 다른 확장자는 제외."""
        mp3 = self._touch("a.mp3")
        txt = self._touch("b.txt")
        result = collect_mp3_paths([mp3, txt])
        self.assertEqual(result, [mp3])

    def test_extension_case_insensitive(self):
        """대소문자 무시(.MP3/.Mp3 도 포함)."""
        up = self._touch("A.MP3")
        mixed = self._touch("B.Mp3")
        result = collect_mp3_paths([up, mixed])
        self.assertEqual(set(result), {up, mixed})

    def test_folder_non_recursive(self):
        """recurse=False 면 그 폴더의 직속 .mp3 만, 정렬 순서로."""
        b = self._touch("sub", "b.mp3")   # noqa: F841 - 하위는 제외되어야 함
        a1 = self._touch("a1.mp3")
        a2 = self._touch("a2.mp3")
        result = collect_mp3_paths([self.root], recurse=False)
        # 직속 두 개만, 파일명 정렬(sorted) 순.
        self.assertEqual(result, [a1, a2])

    def test_folder_recursive_includes_subdirs(self):
        """recurse=True 면 하위 폴더의 .mp3 까지 모은다."""
        top = self._touch("top.mp3")
        deep = self._touch("x", "y", "deep.mp3")
        result = collect_mp3_paths([self.root], recurse=True)
        self.assertEqual(set(result), {top, deep})

    def test_empty_when_no_mp3(self):
        """.mp3 가 없으면 빈 리스트."""
        self._touch("only.txt")
        self.assertEqual(collect_mp3_paths([self.root]), [])


@unittest.skipUnless(_HAVE_GUI, "PySide6/gui not importable")
class TestFileModelIndex(unittest.TestCase):
    """FileTableModel._index 불변식과 find_row_by_path O(1) 조회 정확성.

    불변식: 언제나 모든 행 r 에 대해 find_row_by_path(rows[r].path) == r,
    그리고 목록에 없는 경로는 None. add(append)·remove(재빌드)·clear·중복 add
    전 경로에서 이 성질이 유지되는지 확인한다.
    """

    def _make(self, n: int) -> tuple[FileTableModel, list[str]]:
        m = FileTableModel()
        paths = [f"/music/track_{i}.mp3" for i in range(n)]
        m.add_paths(paths)
        return m, paths

    def _assert_index_consistent(self, m: FileTableModel):
        """현재 모델의 모든 행에 대해 path→row 조회가 실제 위치와 맞는지."""
        for r in range(m.row_count()):
            fr = m.get_row(r)
            self.assertIsNotNone(fr)
            self.assertEqual(m.find_row_by_path(fr.path), r)

    def test_add_then_lookup(self):
        m, paths = self._make(5)
        self._assert_index_consistent(m)
        for i, p in enumerate(paths):
            self.assertEqual(m.find_row_by_path(p), i)

    def test_missing_path_returns_none(self):
        m, _paths = self._make(3)
        self.assertIsNone(m.find_row_by_path("/music/nope.mp3"))

    def test_duplicate_add_ignored(self):
        """이미 있는 경로 재추가는 무시되고 인덱스가 어긋나지 않는다."""
        m, paths = self._make(3)
        added = m.add_paths(paths)  # 전부 중복
        self.assertEqual(added, [])
        self.assertEqual(m.row_count(), 3)
        self._assert_index_consistent(m)

    def test_remove_rebuilds_index(self):
        """중간 행 삭제 후 뒤 행 인덱스가 밀려도 조회가 정확하다(_index 재빌드)."""
        m, paths = self._make(5)
        # 가운데(1)·(3) 삭제 → 남는 건 0,2,4.
        m.remove_rows([1, 3])
        self.assertEqual(m.row_count(), 3)
        remaining = [paths[0], paths[2], paths[4]]
        for i, p in enumerate(remaining):
            self.assertEqual(m.find_row_by_path(p), i)
        # 삭제된 경로는 조회되지 않는다.
        self.assertIsNone(m.find_row_by_path(paths[1]))
        self.assertIsNone(m.find_row_by_path(paths[3]))
        self._assert_index_consistent(m)

    def test_clear_empties_index(self):
        m, paths = self._make(4)
        m.clear()
        self.assertEqual(m.row_count(), 0)
        for p in paths:
            self.assertIsNone(m.find_row_by_path(p))

    def test_add_after_remove_appends_correctly(self):
        """삭제 후 재추가 시 새 경로가 올바른 새 인덱스로 등록된다."""
        m, paths = self._make(3)
        m.remove_rows([0])                 # 남는 건 track_1, track_2 (행 0,1)
        new_added = m.add_paths(["/music/new.mp3"])
        self.assertEqual(new_added, [2])   # 맨 끝(행 2)에 추가
        self.assertEqual(m.find_row_by_path("/music/new.mp3"), 2)
        self._assert_index_consistent(m)


@unittest.skipUnless(_HAVE_GUI, "PySide6/gui not importable")
class TestRecomputeTarget(unittest.TestCase):
    """recompute_target: 목표만 바꿔 재표시. 비파괴·no_tag 처리·수식."""

    def _ok_result(self, track_db: float, target_db: float) -> dict:
        """analyze_file 이 낼 법한 최소 ok result 씨앗(수식 검증용)."""
        return {
            "status": "ok",
            "target_db": target_db,
            "track_db": track_db,
            "volume": None,        # recompute 가 다시 채울 값들
            "steps": None,
            "track_gain_db": None,
            "peak": 0.5,
            "curr_max_amp": 16384,  # 0.5 * 32768
            "min_gain": 100,
            "max_gain": 150,
            "clip_state": "none",
        }

    def test_does_not_mutate_input(self):
        """원본 dict 를 변경하지 않고 새 dict 를 반환한다(비파괴 계약)."""
        seed = self._ok_result(track_db=5.0, target_db=DEFAULT_TARGET_DB)
        snapshot = dict(seed)
        out = recompute_target(seed, 96.0)
        self.assertEqual(seed, snapshot)      # 입력 불변
        self.assertIsNot(out, seed)           # 새 객체
        self.assertEqual(out["target_db"], 96.0)

    def test_volume_is_89_minus_raw(self):
        """Volume = 89 - track_db (원본 DispJunk, modify_db 상쇄)."""
        seed = self._ok_result(track_db=4.0, target_db=DEFAULT_TARGET_DB)
        out = recompute_target(seed, DEFAULT_TARGET_DB)
        self.assertAlmostEqual(out["volume"], DEFAULT_TARGET_DB - 4.0, places=1)

    def test_no_tag_only_updates_target(self):
        """status != ok 면 표시값을 만들지 않고 target 만 바꾼다."""
        seed = {
            "status": "no_tag", "target_db": DEFAULT_TARGET_DB,
            "track_db": None, "volume": None, "steps": None,
            "track_gain_db": None, "peak": None, "curr_max_amp": None,
            "min_gain": None, "max_gain": None, "clip_state": "none",
        }
        out = recompute_target(seed, 92.0)
        self.assertEqual(out["target_db"], 92.0)
        self.assertIsNone(out["volume"])
        self.assertIsNone(out["steps"])

    def test_steps_track_consistency(self):
        """steps 와 track_gain_db 가 서로 정합(track_gain_db = steps*DB_PER_STEP)."""
        seed = self._ok_result(track_db=6.0, target_db=DEFAULT_TARGET_DB)
        out = recompute_target(seed, DEFAULT_TARGET_DB)
        self.assertAlmostEqual(
            out["track_gain_db"], out["steps"] * DB_PER_STEP, places=1)


@unittest.skipUnless(_HAVE_GUI, "PySide6/gui not importable")
class TestShiftAfterApply(unittest.TestCase):
    """shift_after_apply: 적용 후 재표시. steps 0 수렴·peak 이동·비파괴."""

    def _ok_result(self, track_db: float,
                   curr_max_amp: float | None = 16384) -> dict:
        return {
            "status": "ok",
            "target_db": DEFAULT_TARGET_DB,
            "track_db": track_db,
            "volume": DEFAULT_TARGET_DB - track_db,
            "steps": None,
            "track_gain_db": None,
            "peak": None if curr_max_amp is None else curr_max_amp / 32768.0,
            "curr_max_amp": curr_max_amp,
            "min_gain": 100,
            "max_gain": 150,
            "clip_state": "none",
        }

    def test_does_not_mutate_input(self):
        seed = self._ok_result(track_db=3.0 * DB_PER_STEP)
        snapshot = dict(seed)
        out = shift_after_apply(seed, 3)
        self.assertEqual(seed, snapshot)
        self.assertIsNot(out, seed)

    def test_steps_converge_to_zero(self):
        """정수 스텝 배수만큼 적용하면 적용 후 남은 steps 는 0 으로 수렴한다.

        track_db = k*DB_PER_STEP, applied_steps = k → new_track_db = 0 →
        db_to_steps(0) = 0. 부호 방향(raw 를 낮춤)이 뒤집히면 이 성질이 깨진다
        (9항목 표시 수식 함정 2 회귀 감지).
        """
        for k in (1, 3, 5):
            with self.subTest(k=k):
                seed = self._ok_result(track_db=k * DB_PER_STEP)
                out = shift_after_apply(seed, k)
                self.assertEqual(out["steps"], 0)
                self.assertAlmostEqual(out["track_db"], 0.0, places=6)

    def test_track_db_lowered_by_applied(self):
        """new_track_db = track_db - applied_steps * DB_PER_STEP."""
        seed = self._ok_result(track_db=10.0)
        out = shift_after_apply(seed, 2)
        self.assertAlmostEqual(
            out["track_db"], 10.0 - 2 * DB_PER_STEP, places=6)

    def test_peak_scaled_by_applied(self):
        """curr_max_amp *= 2^(applied_steps/4) (클립 기준값 이동)."""
        seed = self._ok_result(track_db=8.0, curr_max_amp=10000)
        out = shift_after_apply(seed, 4)  # 2^(4/4) = 2배
        self.assertEqual(out["curr_max_amp"], round(10000 * 2.0))

    def test_none_peak_stays_none(self):
        """curr_max_amp 가 없으면(None) 그대로 두고 clip 은 none."""
        seed = self._ok_result(track_db=5.0, curr_max_amp=None)
        out = shift_after_apply(seed, 2)
        self.assertIsNone(out["curr_max_amp"])
        self.assertEqual(out["clip_state"], "none")


if __name__ == "__main__":
    unittest.main()
