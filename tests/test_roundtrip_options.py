"""② round-trip 무손실 + 옵션 파싱 + 채널 모드별 -l 동작.

모든 테스트는 원본의 tempfile 사본에서만 동작한다(11항목 영구 제약).
무손실 판정은 오디오 프레임 구간 해시로 한다(audio_body_sha256; 앞쪽 ID3v2·
끝쪽 APE/ID3v1/Lyrics3 꼬리 배제).

게인 방향 주의: 변형 fixture(test_mono_44k/test_stereo_44k)는 max global_gain
이 255 에 붙어 있어(오른쪽 채널 255, 왼쪽 252) +N 을 먼저 적용하면 상한 255
클램프로 정보가 소실되어 round-trip 이 비가역이 된다(원본 _apply_one 규칙 동일).
따라서 round-trip 은 음수 스텝 먼저(-3, 내렸다) 후 복원(+3 또는 undo)으로 한다.
이 fixture 들은 min 이 141~142 라 하한(0)·0-gain 클램프에서 멀어 안전하다.
"""

from __future__ import annotations

import unittest

from tests._support import BaseGainTest

# 채널 모드별 fixture 파일명.
JOINT_STEREO = "Debussy - Arabesque No.1.mp3"   # mode 1
MONO = "test_mono_44k.mp3"                       # mode 3
STEREO = "test_stereo_44k.mp3"                   # mode 0


class RoundTripTest(BaseGainTest):
    """-g -N 적용 후 -u(undo) 로 오디오 프레임이 비트 동일 복원되는지.

    음수 방향을 쓰는 이유는 모듈 docstring 참조(255 클램프 회피).
    """

    def _assert_roundtrip(self, name: str):
        copy = self.copy_fixture(name)
        before = self.audio_body_sha256(copy)

        # -3: 상한 255 클램프를 피하기 위해 먼저 내린다.
        r1 = self.run_cli(["-g", "-3", copy])
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        after_apply = self.audio_body_sha256(copy)
        self.assertNotEqual(before, after_apply,
                            "gain apply did not change audio body")

        # undo: 기록된 역방향 값(+3)을 적용해 원복.
        r2 = self.run_cli(["-u", copy])
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        after_undo = self.audio_body_sha256(copy)
        self.assertEqual(before, after_undo,
                         "undo did not restore audio body bit-for-bit")

    def test_roundtrip_joint_stereo(self):
        self._assert_roundtrip(JOINT_STEREO)

    def test_roundtrip_mono(self):
        self._assert_roundtrip(MONO)

    def test_roundtrip_stereo(self):
        self._assert_roundtrip(STEREO)


class SingleChannelGainTest(BaseGainTest):
    """-l <채널> <스텝>: stereo/dual 은 정상, mono/joint 는 거부.

    stereo round-trip 은 음수 먼저(-3) 후 복원(+3)으로 한다(255 클램프 회피).
    """

    def test_l_on_stereo_roundtrip(self):
        # 순수 stereo(mode 0): 왼쪽 채널 -3 적용 후 +3 로 프레임 복원.
        copy = self.copy_fixture(STEREO)
        before = self.audio_body_sha256(copy)

        r1 = self.run_cli(["-l", "0", "-3", copy])
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        self.assertNotEqual(before, self.audio_body_sha256(copy))

        r2 = self.run_cli(["-l", "0", "3", copy])
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        self.assertEqual(before, self.audio_body_sha256(copy),
                         "left-channel -3/+3 did not round-trip")

    def test_l_right_channel_on_stereo(self):
        # 오른쪽 채널(1)도 적용·복원되는지. 오른쪽 max 가 255 라 음수 먼저 필수.
        copy = self.copy_fixture(STEREO)
        before = self.audio_body_sha256(copy)

        r1 = self.run_cli(["-l", "1", "-3", copy])
        self.assertEqual(r1.returncode, 0, msg=r1.stderr)
        r2 = self.run_cli(["-l", "1", "3", copy])
        self.assertEqual(r2.returncode, 0, msg=r2.stderr)
        self.assertEqual(before, self.audio_body_sha256(copy),
                         "right-channel -3/+3 did not round-trip")

    def test_l_on_mono_rejected(self):
        # mono(mode 3): 단일채널 게인 거부(비정상 종료 또는 미수정).
        copy = self.copy_fixture(MONO)
        before = self.audio_body_sha256(copy)
        r = self.run_cli(["-l", "0", "3", copy])
        # 거부는 비정상 종료로 나타나야 한다.
        self.assertNotEqual(r.returncode, 0,
                            "mono -l should be rejected")
        # 그리고 파일 프레임은 바뀌지 않아야 한다.
        self.assertEqual(before, self.audio_body_sha256(copy),
                         "rejected -l must not modify audio body")

    def test_l_on_joint_stereo_rejected(self):
        # joint stereo(mode 1): 단일채널 게인 거부.
        copy = self.copy_fixture(JOINT_STEREO)
        before = self.audio_body_sha256(copy)
        r = self.run_cli(["-l", "0", "3", copy])
        self.assertNotEqual(r.returncode, 0,
                            "joint-stereo -l should be rejected")
        self.assertEqual(before, self.audio_body_sha256(copy),
                         "rejected -l must not modify audio body")


class OptionParsingTest(BaseGainTest):
    """-v / -h / -? 등 즉시 동작 옵션은 음원 없이도 종료코드 0."""

    def test_version(self):
        r = self.run_cli(["-v"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)

    def test_help(self):
        r = self.run_cli(["-h"])
        self.assertEqual(r.returncode, 0, msg=r.stderr)
        combined = (r.stdout or "") + (r.stderr or "")
        # 영문화 확인: 한글 안내가 남아 있지 않아야 한다(대표 토큰만 점검).
        self.assertNotIn("사용법", combined)


if __name__ == "__main__":
    unittest.main()
