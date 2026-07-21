"""Album 계층 통합 테스트(1단계 코어 검증).

검증 항목:
  1) group_by_album 순수 로직: 폴더별/전체 그룹핑 + 그룹 내 순서 보존.
  2) 스트리밍=통짜 동일성(앨범 확장): api 경로(analyze_album_file →
     album_gain_from_files)가 CLI 통짜 경로(track_histogram 누적 →
     gain_from_histograms)와 비트 단위로 같은 album_db·peak·min/max 를 냄.
     (TrackAnalyzer 스트리밍=통짜는 test_streaming_analysis 에서 이미 검증됨.
      여기서는 그 동일성이 앨범 집계까지 이어짐을 diff=0 으로 고정한다.)
  3) apply_file_album_gain 이 track+album 태그를 둘 다 기록(원본 앨범 게인
     곡별 루프 재현). 사본에서만 동작하며 원본은 BaseGainTest 가드가 지킨다.

원본 음원 불간섭: 모든 파일 작업은 tempfile 사본에서만(copy_fixture).
"""

from __future__ import annotations

import os

from tests._support import BaseGainTest, fixture_path

from gaindb.decode import decode_pcm
from gaindb.analysis import (
    track_histogram, gain_from_histograms, track_peak, NOT_ENOUGH_SAMPLES,
)
from gaindb.writer import scan_gain
from gaindb.tag import read_mp3gain_tags
from gaindb import api


# 한 "앨범"으로 묶을 44.1k fixture 후보(있는 것만 사용).
_ALBUM_FIXTURES = [
    "Debussy - Arabesque No.1.mp3",
    "test_stereo_44k.mp3",
    "test_mono_44k.mp3",
]


class GroupByAlbumTest(BaseGainTest):
    """group_by_album 순수 로직(파일 불필요)."""

    def test_each_folder_is_album_groups_by_dirname(self):
        paths = [
            r"C:\music\albumA\01.mp3",
            r"C:\music\albumA\02.mp3",
            r"C:\music\albumB\01.mp3",
        ]
        groups = api.group_by_album(paths, each_folder_is_album=True)
        self.assertEqual(len(groups), 2)
        # 폴더별로 정확히 나뉜다.
        keys = {os.path.basename(k) for k in groups}
        self.assertEqual(keys, {"albumA", "albumB"})
        # 그룹 내 입력 순서 보존.
        a_key = next(k for k in groups if k.endswith("albumA"))
        self.assertEqual(len(groups[a_key]), 2)
        self.assertTrue(groups[a_key][0].endswith("01.mp3"))
        self.assertTrue(groups[a_key][1].endswith("02.mp3"))

    def test_whole_list_single_group(self):
        paths = [
            r"C:\music\albumA\01.mp3",
            r"C:\music\albumB\01.mp3",
        ]
        groups = api.group_by_album(paths, each_folder_is_album=False)
        self.assertEqual(len(groups), 1)
        (only,) = list(groups.values())
        self.assertEqual(len(only), 2)  # 전부 한 그룹

    def test_empty_input(self):
        self.assertEqual(api.group_by_album([], True), {})
        self.assertEqual(api.group_by_album([], False), {})


class AlbumStreamingEqualsBulkTest(BaseGainTest):
    """api 스트리밍 앨범 집계 = CLI 통짜 경로(동일성 diff=0)."""

    def _available(self):
        got = []
        for name in _ALBUM_FIXTURES:
            try:
                got.append(str(fixture_path(name)))
            except Exception:
                continue
        return got

    def test_album_aggregate_matches_bulk(self):
        paths = self._available()
        if len(paths) < 2:
            self.skipTest("need >=2 44.1k fixtures for an album test")

        # --- (A) CLI 통짜 경로: track_histogram(통짜 decode) 누적 + 집계 ---
        hists = []
        bulk_peak = 0.0
        bulk_max = 0
        bulk_min = 255
        for p in paths:
            left, right, sr = decode_pcm(p)
            hists_i = track_histogram(left, right, sr)
            hists.append(hists_i)
            pk = track_peak(left, right)
            del left, right
            mn, mx = scan_gain(p)
            if pk > bulk_peak:
                bulk_peak = pk
            if mx is not None and mx > bulk_max:
                bulk_max = mx
            if mn is not None and mn < bulk_min:
                bulk_min = mn
        bulk_db = gain_from_histograms(hists)
        self.assertIsNot(bulk_db, NOT_ENOUGH_SAMPLES)

        # --- (B) api 스트리밍 경로: analyze_album_file → album_gain_from_files ---
        per = [api.analyze_album_file(p) for p in paths]
        agg = api.album_gain_from_files(per)
        self.assertEqual(agg["status"], "ok")

        # --- 동일성: 앨범 dB·peak·min/max 가 비트 단위로 같아야 한다 ---
        self.assertEqual(agg["album_db"], bulk_db)
        self.assertEqual(agg["album_peak"], bulk_peak)
        self.assertEqual(agg["album_min"], bulk_min)
        self.assertEqual(agg["album_max"], bulk_max)


class ApplyFileAlbumGainTagTest(BaseGainTest):
    """apply_file_album_gain 이 track+album 태그를 둘 다 기록하는지(사본)."""

    def test_writes_both_track_and_album_tags(self):
        # 앨범 후보 중 존재하는 것으로 2곡 사본 구성.
        names = []
        for name in _ALBUM_FIXTURES:
            try:
                fixture_path(name)
            except Exception:
                continue
            names.append(name)
        if len(names) < 2:
            self.skipTest("need >=2 44.1k fixtures for an album apply test")
        names = names[:2]
        copies = [self.copy_fixture(n) for n in names]

        # 사본을 앨범으로 분석·집계.
        per = [api.analyze_album_file(p) for p in copies]
        agg = api.album_gain_from_files(per)
        self.assertEqual(agg["status"], "ok")

        # 각 곡에 앨범 게인 적용(target 은 기본 89 → offset 0).
        for p, seed in zip(copies, per):
            res = api.apply_file_album_gain(
                p, agg["album_db"], agg["album_peak"],
                agg["album_min"], agg["album_max"], track_seed=seed,
            )
            self.assertIn(res["status"], ("ok", "no_change"))

        # 적용 후 각 곡 태그에 track_gain 과 album_gain 이 둘 다 있어야 한다.
        for p in copies:
            info, _ = read_mp3gain_tags(p)
            self.assertTrue(info.have_track_gain,
                            f"track gain tag missing: {p}")
            self.assertTrue(info.have_album_gain,
                            f"album gain tag missing: {p}")
