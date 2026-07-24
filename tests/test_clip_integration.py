"""③-c 클립 통합 테스트 (CLI 경로).

원본 mp3gain 의 클립 처리 동작을 gaindb_cli.py 경로에서 재현·검증한다.
클립은 -m 큰 스텝으로 인위 유도한다(-m 은 양자화 후 스텝에 더해져 클립 조건
max_sample * 2^(steps/4) > 32767 을 확실히 넘긴다).

- -k autoClip(Track): 클립 조건이면 스텝을 상한으로 낮춰 적용.
  stdout "Applying auto-clipped mp3 gain change of N to <file>"
        + "(Original suggested gain was M)".
- -c 미지정 프롬프트: 클립 조건이면 stderr 에 WARNING + "Make change? [y/n]:".
  stdin y -> 적용(오디오 변화), n/EOF -> 미적용(오디오 불변).
- -a -k autoClip(Album): 하향은 루프 밖 1회.
  stdout "Applying auto-clipped mp3 gain change of N to album"
        + "(Original suggested gain was M)".

원본 음원 불간섭: 모든 작업은 tempfile 사본에서만(BaseGainTest).
"""

from __future__ import annotations

from tests._support import BaseGainTest


class TrackAutoClipTest(BaseGainTest):
    """-k Track autoClip: 큰 스텝을 상한으로 낮춰 적용."""

    FIXTURE = "test_gain_44k.mp3"

    def test_autoclip_lowers_and_applies(self):
        path = self.copy_fixture(self.FIXTURE)
        # -r 로 Track 적용 경로 진입 + -m 30 으로 큰 스텝 → -k 가 상한으로 하향.
        r = self.run_cli(["-r", "-k", "-m", "30", path])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("Applying auto-clipped mp3 gain change of", r.stdout)
        self.assertIn("(Original suggested gain was", r.stdout)


class ClipPromptTest(BaseGainTest):
    """-c 미지정 시 stdin y/n/EOF 프롬프트."""

    FIXTURE = "test_gain_44k.mp3"

    def test_prompt_appears_when_clipping(self):
        path = self.copy_fixture(self.FIXTURE)
        # -c 없이 클립 조건 → 프롬프트가 stderr 에 떠야 한다. n 으로 거부.
        r = self.run_cli(["-r", "-m", "30", path], stdin="n\n")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("may clip with mp3 gain change", r.stderr)
        self.assertIn("Make change? [y/n]:", r.stderr)

    def test_prompt_no_declines_apply(self):
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)
        r = self.run_cli(["-r", "-m", "30", path], stdin="n\n")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # n -> 미적용: 오디오 프레임 불변.
        self.assertEqual(before, self.audio_body_sha256(path),
                         "declining the prompt must not change audio")

    def test_prompt_yes_applies(self):
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)
        r = self.run_cli(["-r", "-m", "30", path], stdin="y\n")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        # y -> 적용: 오디오 프레임 변화.
        self.assertNotEqual(before, self.audio_body_sha256(path),
                            "accepting the prompt must change audio")

    def test_prompt_eof_declines(self):
        path = self.copy_fixture(self.FIXTURE)
        before = self.audio_body_sha256(path)
        # stdin 없음(EOF) -> 원본 동작상 거부(N). 오디오 불변.
        r = self.run_cli(["-r", "-m", "30", path], stdin="")
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertEqual(before, self.audio_body_sha256(path),
                         "EOF on prompt must decline (no change)")


class AlbumAutoClipTest(BaseGainTest):
    """-a -k Album autoClip: 하향은 루프 밖 1회."""

    def test_album_autoclip_once(self):
        a = self.copy_fixture("test_gain_44k.mp3")
        b = self.copy_fixture("test_gain_48k.mp3")
        r = self.run_cli(["-a", "-k", "-m", "30", a, b])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        self.assertIn("Applying auto-clipped mp3 gain change of", r.stdout)
        self.assertIn("to album", r.stdout)
        self.assertIn("(Original suggested gain was", r.stdout)


if __name__ == "__main__":
    import unittest
    unittest.main()
