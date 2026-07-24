# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
"""테스트 fixture 합성 생성기 (git 공개, 산출물은 _local/test_audio/ 로).

저작권 음원을 쓰지 않는다(완전 독립 노선). 고정 시드 대역제한 노이즈 +
다구간 진폭 포락선 + 좌우 비대칭으로 시드 PCM 을 합성하고, ffmpeg(libmp3lame)
로 44.1k/48k 기준 fixture 를 인코딩한 뒤, 같은 시드에서 -ar/-ac 변형으로
저샘플레이트·mono·stereo 파생 fixture 를 만든다.

재현성: numpy 고정 시드라 매 실행이 비트 동일 PCM 을 낸다.

산출 위치: 환경변수 GAINDB_TEST_MP3_DIR 우선, 없으면 리포 루트의
_local/test_audio/ (git 제외). 실행 시 알려진 fixture 이름을 먼저 삭제(전량
재생성)한 뒤 채운다.

생성 직후 gaindb.frame.parse_file 로 각 산출물의 mpegver/samplerate/nchan/
granule/global_gain(min·max) 을 assert 검증한다. 하나라도 어긋나면 무엇이
틀렸는지 출력하고 비정상 종료한다(구멍 없는 fixture 보장).

사용법:
    python tests/_gen_fixtures.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np
from scipy.signal import butter, sosfilt

# 리포 루트 = 이 파일(tests/_gen_fixtures.py)의 부모의 부모.
REPO_ROOT = Path(__file__).resolve().parent.parent

# 산출 디렉터리: 환경변수 우선, 없으면 _local/test_audio/.
_env_dir = os.environ.get("GAINDB_TEST_MP3_DIR")
OUT_DIR = Path(_env_dir).resolve() if _env_dir else REPO_ROOT / "_local" / "test_audio"

# 재현성 고정 시드(바꾸면 fixture 내용이 바뀐다 — 함부로 바꾸지 말 것).
_RNG_SEED = 20260724

# 시드 신호 파라미터.
_SEED_RATE = 44100          # 시드는 44.1k 로 만들고 파생은 리샘플.
_SEED_SECONDS = 2.5         # 짧게(테스트 속도). 50ms 윈도우 50개+ 확보.
_BAND_LO_HZ = 200.0         # 저역 중심 대역통과 하한.
_BAND_HI_HZ = 3000.0        # 상한(8k 나이키스트 4k 이하라 저샘플레이트도 안전).
_PEAK_HEADROOM_DB = -0.5    # int16 변환 시 클리핑 방지 헤드룸(피크를 -0.5dBFS 로).

# 다구간 진폭 포락선(dBFS). 최고 구간을 풀 스케일 근처로 올려 인코더가 max
# global_gain(255)을 쓰도록 유도한다(round-trip 방향 제약의 근거). 구간 경계는
# 50ms 윈도우 배수를 피해 자투리 이월 경로도 태운다.
_ENVELOPE_LEVELS_DB = (-18.0, -8.0, -0.5)

# 기준 fixture(시드에서 직접 인코딩).
#   name -> (samplerate, channels, joint)  joint=None 이면 ffmpeg 기본.
_BASE_FIXTURES = {
    "test_gain_44k.mp3": (44100, 2, None),   # 44.1k joint stereo (MPEG1, mode 1)
    "test_gain_48k.mp3": (48000, 2, None),   # 48k joint stereo (MPEG1, mode 1)
}

# 파생 fixture(시드 WAV 에서 -ar/-ac 변형).
#   name -> (samplerate, channels, joint)
_DERIVED_FIXTURES = {
    "test_mono_44k.mp3":  (44100, 1, None),    # mode 3
    "test_stereo_44k.mp3": (44100, 2, 0),      # mode 0 (joint off)
    "test_32k.mp3":       (32000, 2, None),    # MPEG1
    "test_24k.mp3":       (24000, 2, None),    # MPEG2
    "test_22k.mp3":       (22050, 2, None),    # MPEG2
    "test_16k.mp3":       (16000, 2, None),    # MPEG2
    "test_12k.mp3":       (12000, 2, None),    # MPEG2.5
    "test_11k.mp3":       (11025, 2, None),    # MPEG2.5
    "test_8k.mp3":        (8000,  2, None),    # MPEG2.5
    "test_mono_24k.mp3":  (24000, 1, None),    # MPEG2, mode 3
    "test_mono_12k.mp3":  (12000, 1, None),    # MPEG2.5, mode 3
}

# parse_file 검증 기대: name -> (mpegver, samplerate, nchan, granule)
#   mpegver: 3=MPEG1, 2=MPEG2, 0=MPEG2.5   granule: MPEG1=2, else=1
_EXPECT = {
    "test_gain_44k.mp3":  (3, 44100, 2, 2),
    "test_gain_48k.mp3":  (3, 48000, 2, 2),
    "test_mono_44k.mp3":  (3, 44100, 1, 2),
    "test_stereo_44k.mp3": (3, 44100, 2, 2),
    "test_32k.mp3":       (3, 32000, 2, 2),
    "test_24k.mp3":       (2, 24000, 2, 1),
    "test_22k.mp3":       (2, 22050, 2, 1),
    "test_16k.mp3":       (2, 16000, 2, 1),
    "test_12k.mp3":       (0, 12000, 2, 1),
    "test_11k.mp3":       (0, 11025, 2, 1),
    "test_8k.mp3":        (0,  8000, 2, 1),
    "test_mono_24k.mp3":  (2, 24000, 1, 1),
    "test_mono_12k.mp3":  (0, 12000, 1, 1),
}

# 44.1k 계열은 음수 스텝 round-trip(-N 먼저 내렸다 복원)이 안전해야 한다.
# 필요한 성질은 (a) max global_gain 이 상한(255)에서 여유가 있어 인위 양수
# 스텝(-m)을 줘도 클램프 위험이 낮고, (b) min 이 하한(0)에서 멀어 음수 스텝이
# 0-gain 클램프에 안 걸리는 것. 인코딩 결과에 의존하는 "정확히 255"는 특정
# 인코더에 취약하므로 강제하지 않는다(옛 fixture 의 우연한 성질이었을 뿐,
# 테스트가 요구하는 조건이 아니다 — round-trip 은 -3→+3 방향이라 상한 무관).
_ROUNDTRIP_SAFE = {
    "test_gain_44k.mp3", "test_mono_44k.mp3", "test_stereo_44k.mp3",
}

# 음수 스텝 round-trip 안전 여유: min 이 이 값보다 커야(0-gain 클램프 회피),
# max 가 (255 - 이 값)보다 작아야(상한 여유) 한다.
_ROUNDTRIP_MARGIN = 8


def _db_to_lin(db: float) -> float:
    return 10.0 ** (db / 20.0)


def _make_seed_stereo() -> np.ndarray:
    """(N, 2) float32 시드 신호를 합성한다. 값 범위는 대략 [-1, 1].

    구성: 대역제한(200~3000Hz) 노이즈 + 다구간 진폭 포락선 + 좌우 비대칭.
    최고 구간에는 톤 성분을 보강해 프레임 에너지를 높인다(인코더가 max
    global_gain 255 를 쓰도록 유도 — round-trip 전제).
    """
    rng = np.random.default_rng(_RNG_SEED)
    n = int(_SEED_RATE * _SEED_SECONDS)
    t = np.arange(n, dtype=np.float64) / _SEED_RATE

    # 좌우 독립 백색소음 → 대역통과로 음악 비슷한 스펙트럼.
    white = rng.standard_normal((n, 2)).astype(np.float64)
    sos = butter(4, [_BAND_LO_HZ, _BAND_HI_HZ], btype="band", fs=_SEED_RATE,
                 output="sos")
    band = sosfilt(sos, white, axis=0)
    # 노이즈 성분을 자체 피크로 정규화(뒤에서 포락선을 곱하기 위한 기준화).
    npk = float(np.max(np.abs(band)))
    if npk > 0.0:
        band /= npk

    # 다구간 진폭 포락선(구간 경계는 50ms 윈도우 배수를 일부러 피한다).
    env = np.ones(n, dtype=np.float64)
    seg = n // len(_ENVELOPE_LEVELS_DB)
    last_start = (len(_ENVELOPE_LEVELS_DB) - 1) * seg
    for i, db in enumerate(_ENVELOPE_LEVELS_DB):
        start = i * seg
        end = n if i == len(_ENVELOPE_LEVELS_DB) - 1 else (i + 1) * seg
        env[start:end] = _db_to_lin(db)
    band *= env[:, None]

    # 최고 구간(마지막 세그먼트)에 저역 톤(500Hz·1200Hz)을 보강해 프레임 에너지를
    # 높인다. 톤은 8k 나이키스트(4k) 이하라 저샘플레이트 파생에서도 살아남는다.
    tone = (0.6 * np.sin(2 * np.pi * 500.0 * t)
            + 0.4 * np.sin(2 * np.pi * 1200.0 * t))
    tone_env = np.zeros(n, dtype=np.float64)
    tone_env[last_start:] = 1.0
    tone *= tone_env
    band[:, 0] += tone
    band[:, 1] += tone

    # 좌우 비대칭: 오른쪽에 약한 진폭차 + 소량 지연으로 채널 독립성 확보.
    band[:, 1] *= 0.85
    band[1:, 1] = band[:-1, 1]  # 1 샘플 지연(위상차)

    # 정규화: 전체 피크를 -0.5dBFS 로 맞춘다(int16 클리핑 방지 + 255 유도).
    peak = float(np.max(np.abs(band)))
    if peak > 0.0:
        band *= _db_to_lin(_PEAK_HEADROOM_DB) / peak
    return band.astype(np.float32)


def _write_wav(path: Path, stereo: np.ndarray) -> None:
    """(N, 2) float [-1,1] 을 16-bit PCM WAV(44.1k stereo)로 쓴다."""
    ints = np.clip(stereo, -1.0, 1.0)
    ints = (ints * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(2)
        w.setsampwidth(2)
        w.setframerate(_SEED_RATE)
        w.writeframes(ints.tobytes())


def _ffmpeg_encode(src_wav: Path, dst_mp3: Path,
                   samplerate: int, channels: int, joint) -> None:
    """WAV → MP3 인코딩(libmp3lame -q:a 4). joint 지정 시 -joint_stereo."""
    cmd = ["ffmpeg", "-y", "-i", str(src_wav),
           "-ar", str(samplerate), "-ac", str(channels)]
    if joint is not None:
        cmd += ["-joint_stereo", str(joint)]
    cmd += ["-c:a", "libmp3lame", "-q:a", "4", str(dst_mp3)]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError(
            f"ffmpeg failed for {dst_mp3.name}:\n{proc.stderr[-2000:]}")


def _clean_output() -> None:
    """알려진 fixture 를 삭제(디렉터리 통째 삭제는 안 함)."""
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    names = list(_BASE_FIXTURES) + list(_DERIVED_FIXTURES)
    for name in names:
        p = OUT_DIR / name
        if p.is_file():
            p.unlink()
            print(f"  removed old: {name}")


def _verify(name: str) -> None:
    """parse_file 로 fixture 의 기대 성질을 assert. 실패 시 예외."""
    from gaindb.frame import parse_file

    path = OUT_DIR / name
    frames = list(parse_file(str(path)))
    if not frames:
        raise AssertionError(f"{name}: no frames parsed")

    exp_ver, exp_sr, exp_nch, granule = _EXPECT[name]
    first = frames[0]
    if first.mpegver != exp_ver:
        raise AssertionError(
            f"{name}: mpegver {first.mpegver} != {exp_ver}")
    if first.samplerate_hz != exp_sr:
        raise AssertionError(
            f"{name}: samplerate {first.samplerate_hz} != {exp_sr}")
    if first.nchan != exp_nch:
        raise AssertionError(f"{name}: nchan {first.nchan} != {exp_nch}")

    all_gains = [g for fr in frames for g in fr.gains]
    expected_count = len(frames) * granule * exp_nch
    if len(all_gains) != expected_count:
        raise AssertionError(
            f"{name}: gains count {len(all_gains)} != {expected_count}")

    gmin, gmax = min(all_gains), max(all_gains)
    if gmin < 0 or gmax > 255:
        raise AssertionError(f"{name}: global_gain out of range [{gmin},{gmax}]")
    if (gmin, gmax) == (0, 0):
        raise AssertionError(f"{name}: gains all zero (side-info offset wrong?)")

    # round-trip 안전 성질: 음수 스텝 먼저 적용해 복원하는 테스트가 클램프
    # (상한 255 / 하한 0)에 걸리지 않도록 여유가 있어야 한다.
    if name in _ROUNDTRIP_SAFE:
        if gmin < _ROUNDTRIP_MARGIN:
            raise AssertionError(
                f"{name}: min global_gain {gmin} too close to floor 0 "
                f"(need >= {_ROUNDTRIP_MARGIN} for safe negative-step round-trip)")
        if gmax > 255 - _ROUNDTRIP_MARGIN:
            raise AssertionError(
                f"{name}: max global_gain {gmax} too close to ceiling 255 "
                f"(need <= {255 - _ROUNDTRIP_MARGIN} for safe round-trip)")

    tag = "  [rt-safe]" if name in _ROUNDTRIP_SAFE else ""
    print(f"  verified: {name}  ver={first.mpegver} sr={first.samplerate_hz} "
          f"nch={first.nchan} gain=[{gmin},{gmax}]{tag}")


def main() -> int:
    print(f"Output dir: {OUT_DIR}")
    print("Cleaning old fixtures...")
    _clean_output()

    print("Synthesizing seed signal...")
    seed = _make_seed_stereo()

    with tempfile.TemporaryDirectory(prefix="gaindb_gen_") as td:
        seed_wav = Path(td) / "seed.wav"
        _write_wav(seed_wav, seed)

        print("Encoding fixtures...")
        for name, (sr, ch, joint) in {**_BASE_FIXTURES,
                                      **_DERIVED_FIXTURES}.items():
            _ffmpeg_encode(seed_wav, OUT_DIR / name, sr, ch, joint)
            print(f"  encoded: {name}")

    print("Verifying fixtures (parse_file assertions)...")
    for name in {**_BASE_FIXTURES, **_DERIVED_FIXTURES}:
        _verify(name)

    print(f"\nDone. {len(_BASE_FIXTURES) + len(_DERIVED_FIXTURES)} "
          f"fixtures generated in {OUT_DIR}")
    return 0


if __name__ == "__main__":
    # 리포 루트를 import 경로에 넣어 gaindb.frame 을 쓸 수 있게 한다.
    sys.path.insert(0, str(REPO_ROOT))
    sys.exit(main())