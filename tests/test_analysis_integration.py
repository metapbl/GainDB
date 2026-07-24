"""③-a 분석 통합 테스트 (CLI 경로).

원본 mp3gain 의 분석 동작을 gaindb_cli.py 경로에서 재현·검증한다.
- 순수 분석(옵션 없음): stdout 에 Track 제안 라인들, 오디오 프레임 불변.
  (원본은 분석만 해도 dirty 태그를 파일 끝에 기록하므로 전체 파일 해시는
   바뀔 수 있다 — 무결성 판정은 반드시 audio_body_sha256[프레임 구간]으로.)
- -r: Track 적용. 제안 스텝≠0 이면 "Applying mp3 gain change of N to ..."
  (stdout) + 오디오 프레임 변화. ==0 이면 "No changes..." + 불변.
- -a: 다중 파일 Album. "Recommended \"Album\" ..." 라인 + 전 파일 동일 스텝.
- 수치 재검증(1건): 순수 분석 Track dB 가 ffmpeg replaygain 과 허용오차 내.
  (ffmpeg 부재 시 skip. CLI 는 양자화 전 dB 를 출력하므로 라이브러리 검증보다
   느슨한 허용오차로 경로 정합성만 확인.)

원본 음원 불간섭: 모든 작업은 tempfile 사본에서만(11항목, BaseGainTest).
"""

from __future__ import annotations

import re
import shutil
import subprocess
import unittest

from tests._support import BaseGainTest

# CLI 제안 라인 정규식(원본 영문 verbatim 기준).
_RE_TRACK_DB = re.compile(r'Recommended "Track" dB change:\s*(-?\d+\.\d+)')
_RE_TRACK_STEP = re.compile(r'Recommended "Track" mp3 gain change:\s*(-?\d+)')
_RE_APPLYING = re.compile(r'Applying mp3 gain change of (-?\d+) to ')
_RE_ALBUM_DB = re.compile(
    r'Recommended "Album" dB change for all files:\s*(-?\d+\.\d+)')
_RE_ALBUM_STEP = re.compile(
    r'Recommended "Album" mp3 gain change for all files:\s*(-?\d+)')


def _ffmpeg_available() -> bool:
    try:
        subprocess.run(["ffmpeg", "-version"],
                       capture_output=True, check=True)
        return True
    except (OSError, subprocess.CalledProcessError):
        return False


class TrackAnalysisTest(BaseGainTest):
    """순수 분석(옵션 없음)의 제안 출력 + 오디오 불변."""

    def test_pure_analysis_outputs_track_suggestion(self):
        # 어떤 fixture 든 하나 확보(없으면 copy_fixture 가 SkipTest).
        path = self.copy_fixture("test_gain_44k.mp3")
        before = self.audio_body_sha256(path)

        r = self.run_cli([path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        # 원본 Track 제안 라인들이 stdout 에 모두 존재해야 한다.
        self.assertIn('Recommended "Track" dB change:', r.stdout)
        self.assertIn('Recommended "Track" mp3 gain change:', r.stdout)
        self.assertIn("Max PCM sample at current gain:", r.stdout)
        self.assertIn("Max mp3 global gain field:", r.stdout)
        self.assertIn("Min mp3 global gain field:", r.stdout)

        # 순수 분석은 오디오 프레임을 건드리지 않는다(태그는 쓸 수 있음 → 전체
        # 해시가 아니라 audio body 로 판정).
        after = self.audio_body_sha256(path)
        self.assertEqual(before, after,
                         "pure analysis must not modify audio frames")

    def test_database_format_track_row(self):
        path = self.copy_fixture("test_gain_44k.mp3")
        r = self.run_cli(["-o", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # -o: 헤더 + 파일별 탭 구분 행. 헤더 필드 존재 + 데이터 행 파일명 포함.
        self.assertIn("MP3 gain", r.stdout)
        self.assertIn("dB gain", r.stdout)
        # 데이터 행: 경로 + 최소 6개 탭 필드.
        data_lines = [ln for ln in r.stdout.splitlines()
                      if ln.startswith(path)]
        self.assertTrue(data_lines, "database data row for the file missing")
        self.assertGreaterEqual(len(data_lines[0].split("\t")), 6)


class TrackApplyTest(BaseGainTest):
    """-r Track 적용의 오디오 변화 / No changes 분기."""

    def test_apply_track_changes_audio(self):
        path = self.copy_fixture("test_gain_44k.mp3")
        before = self.audio_body_sha256(path)

        r = self.run_cli(["-r", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        m = _RE_APPLYING.search(r.stdout)
        after = self.audio_body_sha256(path)

        if m and int(m.group(1)) != 0:
            # 스텝≠0: 오디오 프레임이 실제로 바뀌어야 한다.
            self.assertNotEqual(before, after,
                                "apply with nonzero step must change audio")
        else:
            # 스텝==0: "No changes..." + 오디오 불변.
            self.assertIn("No changes to", r.stdout)
            self.assertEqual(before, after,
                             "zero-step apply must not change audio")


class AlbumAnalysisTest(BaseGainTest):
    """-a 다중 파일 Album: 제안 라인 + 전 파일 동일 스텝 적용."""

    def _two_fixtures(self):
        # 44.1k + 48k 혼합(있는 것만). 둘 다 있어야 Album 경로가 의미 있음.
        a = self.copy_fixture("test_gain_44k.mp3")
        b = self.copy_fixture("test_gain_48k.mp3")
        return a, b

    def test_album_suggestion_lines(self):
        a, b = self._two_fixtures()
        # 적용 없이 제안만(-a 없이 다중 입력 → Album 제안 자동 출력).
        r = self.run_cli([a, b])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn('Recommended "Album" dB change for all files:', r.stdout)
        self.assertIn('Recommended "Album" mp3 gain change for all files:',
                      r.stdout)

    def test_apply_album_same_step_all_files(self):
        a, b = self._two_fixtures()
        before_a = self.audio_body_sha256(a)
        before_b = self.audio_body_sha256(b)

        r = self.run_cli(["-a", a, b])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        # 적용 스텝 추출: "Applying mp3 gain change of N to <path>..." 각 파일.
        applied = {}
        for ln in r.stdout.splitlines():
            m = _RE_APPLYING.search(ln)
            if m:
                # 라인 끝의 경로로 어느 파일인지 구분.
                if a in ln:
                    applied[a] = int(m.group(1))
                elif b in ln:
                    applied[b] = int(m.group(1))

        # Album 은 전 파일에 단일(동일) 스텝을 적용한다(원본 동작).
        if applied:
            steps = set(applied.values())
            # 0 스텝 파일은 "No changes" 로 빠질 수 있으므로, 적용된 것들끼리
            # 스텝이 하나여야 한다(동일 스텝).
            self.assertEqual(len(steps), 1,
                             f"album must apply a single step, got {applied}")

        after_a = self.audio_body_sha256(a)
        after_b = self.audio_body_sha256(b)
        # 최소한 한 파일은 실제로 바뀌었어야 한다(둘 다 0 스텝인 우연은 배제).
        self.assertTrue(before_a != after_a or before_b != after_b,
                        "album apply changed no audio at all")


@unittest.skipUnless(_ffmpeg_available(), "ffmpeg not available")
class TrackDbNumericTest(BaseGainTest):
    """수치 재검증(1건): CLI Track dB 가 라이브러리 코어 직접 호출과 일치.

    통합 테스트의 목적은 "CLI 진입점이 코어 분석을 올바로 경유하는가"이다.
    코어↔ffmpeg 정확도는 이미 라이브러리 검증(2단계, 0.02dB)이 담당하므로,
    여기서는 CLI stdout 의 Track dB 가 동일 코어를 직접 호출한 값과 일치하는지
    (같은 코드 경로라 사실상 일치) 좁은 허용오차로 확인한다. 디코딩에 ffmpeg 가
    필요하므로 부재 시 skip.
    """

    _TOL_DB = 0.05

    def _library_track_db(self, path: str) -> float:
        from gaindb.decode import decode_pcm
        from gaindb.analysis import track_histogram, gain_from_histograms
        left, right, sample_rate = decode_pcm(path)
        hist = track_histogram(left, right, sample_rate)
        return gain_from_histograms([hist])

    def test_cli_track_db_matches_core(self):
        path = self.copy_fixture("test_gain_44k.mp3")

        ref = self._library_track_db(path)

        r = self.run_cli([path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        m = _RE_TRACK_DB.search(r.stdout)
        self.assertIsNotNone(m, "CLI did not print a Track dB change")
        cli_db = float(m.group(1))

        self.assertLessEqual(
            abs(cli_db - ref), self._TOL_DB,
            f"CLI Track dB {cli_db} vs core {ref} exceeds {self._TOL_DB} dB")
