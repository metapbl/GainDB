"""③-b 태그 통합 테스트 (CLI 경로).

mp3gain 의 태그 동작을 gaindb_cli.py 경로에서 검증한다.
APE(기본) / ID3v2(-s i) 두 경로 각각 write / read / remove / round-trip.

무손실 복원(round-trip) 원칙(9항 영구 제약):
- 반드시 음수 스텝 먼저(-g -3 → -u). 양수 먼저는 255 상한 클램프로 비가역.
- undo 후 MP3GAIN_UNDO 0,0 태그가 남아 전체 파일 해시는 달라질 수 있으므로,
  판정은 audio_body_sha256(프레임 구간)로 한다.
- -r 은 곡 라우드니스에 따라 양수 스텝이 나올 수 있어 무손실 복원 검증엔
  쓰지 않는다. -r 은 "태그 필드가 기록되는가"만 확인한다.

ID3 경로 태그는 --debug-tag(APE 전용)로 못 보므로, -s c -s i(check_tag_only
+ use_id3)로 CLI 가 ID3 태그를 읽어 제안을 출력하는지로 read 를 검증한다
(-s c 가 use_id3 에 따라 해당 태그를 읽는 mp3gain 동작과 일치).

fixture 불간섭: 모든 작업은 tempfile 사본에서만(BaseGainTest).
"""

from __future__ import annotations

from tests._support import BaseGainTest


class ApeTagTest(BaseGainTest):
    """APE 태그(기본 경로) write / read / round-trip / remove."""

    FIXTURE = "test_gain_44k.mp3"

    def test_apply_writes_ape_gain_fields(self):
        # -r 적용 후 APE 태그에 track gain/peak/min-max 필드가 기록되어야 한다.
        path = self.copy_fixture(self.FIXTURE)
        r = self.run_cli(["-r", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        d = self.run_cli(["--debug-tag", path])
        self.assertEqual(d.returncode, 0, msg=d.stderr)
        self.assertIn("APE tag          : yes", d.stdout)
        self.assertIn("track_gain", d.stdout)
        self.assertIn("track_peak", d.stdout)
        self.assertIn("min/max_gain", d.stdout)

    def test_check_tag_reads_back_stored_gain(self):
        # write 후 -s c 로 저장된 값을 다시 읽어 제안을 출력해야 한다(read RT).
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", path]).returncode, 0)

        c = self.run_cli(["-s", "c", path])
        self.assertEqual(c.returncode, 0, msg=c.stderr)
        self.assertIn('Recommended "Track" dB change:', c.stdout)
        self.assertIn("Max mp3 global gain field:", c.stdout)

    def test_direct_gain_undo_roundtrip_ape(self):
        # 음수 스텝 먼저(-g -3) → -u 로 오디오 프레임 비트 동일 복원.
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)

        a = self.run_cli(["-g", "-3", path])
        self.assertEqual(a.returncode, 0, msg=a.stderr)
        self.assertNotEqual(before, self.audio_body_sha256(path),
                            "-g -3 must change audio frames")

        u = self.run_cli(["-u", path])
        self.assertEqual(u.returncode, 0, msg=u.stderr)
        # undo 상태 메시지는 stderr(mp3gain 과 동일한 출력).
        self.assertIn("Undoing mp3gain changes", u.stderr)

        after = self.audio_body_sha256(path)
        self.assertEqual(before, after,
                         "undo must restore audio frames bit-for-bit")

    def test_delete_tag_removes_ape(self):
        # write 후 -s d 로 APE 태그 제거 → --debug-tag 로 태그 없음 확인.
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", path]).returncode, 0)
        # 제거 전 태그 존재.
        self.assertIn("APE tag          : yes",
                      self.run_cli(["--debug-tag", path]).stdout)

        d = self.run_cli(["-s", "d", path])
        self.assertEqual(d.returncode, 0, msg=d.stderr)
        self.assertIn("Deleting tag info of", d.stderr)

        # 제거 후 APE 태그 없음.
        after = self.run_cli(["--debug-tag", path])
        self.assertIn("APE tag          : none", after.stdout)


class Id3TagTest(BaseGainTest):
    """ID3v2 태그(-s i 경로) write / read / round-trip / remove."""

    FIXTURE = "test_gain_44k.mp3"

    def test_apply_and_check_id3(self):
        # -s i 로 ID3v2 태그에 기록 후, -s c -s i 로 다시 읽어 제안 출력(read RT).
        path = self.copy_fixture(self.FIXTURE)
        r = self.run_cli(["-r", "-s", "i", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

        c = self.run_cli(["-s", "c", "-s", "i", path])
        self.assertEqual(c.returncode, 0, msg=c.stderr)
        self.assertIn('Recommended "Track" dB change:', c.stdout)

    def test_direct_gain_undo_roundtrip_id3(self):
        # ID3 경로에서도 음수 스텝 먼저(-g -3 -s i) → -u -s i 무손실 복원.
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)

        a = self.run_cli(["-g", "-3", "-s", "i", path])
        self.assertEqual(a.returncode, 0, msg=a.stderr)
        self.assertNotEqual(before, self.audio_body_sha256(path),
                            "-g -3 must change audio frames")

        u = self.run_cli(["-u", "-s", "i", path])
        self.assertEqual(u.returncode, 0, msg=u.stderr)
        self.assertIn("Undoing mp3gain changes", u.stderr)

        after = self.audio_body_sha256(path)
        self.assertEqual(before, after,
                         "undo must restore audio frames bit-for-bit (id3)")

    def test_delete_tag_id3(self):
        # -s i 로 ID3 태그 기록 후 -s d -s i 로 제거. 제거는 rc 0 이면 충분히
        # 동작한 것으로 보고, 이후 -s c -s i 가 track gain 을 더는 못 읽음을 확인.
        path = self.copy_fixture(self.FIXTURE)
        self.assertEqual(self.run_cli(["-r", "-s", "i", path]).returncode, 0)

        d = self.run_cli(["-s", "d", "-s", "i", path])
        self.assertEqual(d.returncode, 0, msg=d.stderr)

        c = self.run_cli(["-s", "c", "-s", "i", path])
        self.assertEqual(c.returncode, 0, msg=c.stderr)
        # 태그가 제거되었으면 Track 제안 라인이 더는 나오지 않아야 한다.
        self.assertNotIn('Recommended "Track" dB change:', c.stdout)


if __name__ == "__main__":
    import unittest
    unittest.main()