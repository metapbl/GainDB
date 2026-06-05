"""통합 테스트 공통 인프라.

원칙(CLAUDE.md 11항목 영구 제약): 원본 음원을 절대 건드리지 않는다.
- 모든 테스트는 tempfile 사본에서만 동작하고 끝나면 정리한다.
- 원본 무결성 가드: 테스트 전후로 원본 해시를 비교해 오염을 즉시 잡는다.
- 음원은 git 제외라 환경에 없을 수 있으므로, 없으면 SkipTest 로 건너뛴다.

음원 디렉터리는 환경변수 GAINDB_TEST_MP3_DIR 로 지정할 수 있고,
없으면 리포 루트(이 파일 기준 한 단계 위)를 기본으로 본다.
"""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

# 리포 루트 = 이 파일(tests/_support.py)의 부모의 부모.
REPO_ROOT = Path(__file__).resolve().parent.parent

# 통합 CLI 진입점.
CLI_SCRIPT = REPO_ROOT / "mp3gain_cli.py"

# 음원 디렉터리: 환경변수 우선, 없으면 리포 루트.
_env_dir = os.environ.get("GAINDB_TEST_MP3_DIR")
MP3_DIR = Path(_env_dir).resolve() if _env_dir else REPO_ROOT

# 알려진 테스트 음원(파일명 → 설명). git 제외라 부재 가능.
# 새 음원을 추가하면 여기에 등록하면 자동으로 가드·헬퍼가 인식한다.
KNOWN_FIXTURES = {
    "Debussy - Arabesque No.1.mp3": "44.1k joint stereo (MPEG1)",
    "10cm - 사랑은 은하수 다방에서.mp3": "48k joint stereo (MPEG1)",
}


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def fixture_path(name: str) -> Path:
    """알려진 음원의 원본 경로. 없으면 SkipTest."""
    p = MP3_DIR / name
    if not p.is_file():
        raise unittest.SkipTest(f"test fixture not found: {p}")
    return p


def available_fixtures() -> list[Path]:
    """현재 환경에 실제로 존재하는 음원 경로 목록(없으면 빈 리스트)."""
    return [MP3_DIR / n for n in KNOWN_FIXTURES if (MP3_DIR / n).is_file()]


class FixtureGuard:
    """원본 음원 무결성 가드.

    enter 시 존재하는 모든 알려진 음원의 해시를 기록하고,
    verify() 로 변하지 않았는지 확인한다(D-3 오염 사고 재발 방지).
    """

    def __init__(self):
        self._hashes: dict[Path, str] = {}

    def snapshot(self) -> None:
        self._hashes.clear()
        for p in available_fixtures():
            self._hashes[p] = _sha256(p)

    def verify(self) -> None:
        for p, before in self._hashes.items():
            after = _sha256(p)
            if before != after:
                raise AssertionError(
                    f"ORIGINAL FIXTURE WAS MODIFIED: {p}\n"
                    f"  before={before}\n  after ={after}\n"
                    "A test wrote to an original source file. "
                    "All tests must operate on tempfile copies only."
                )


class BaseGainTest(unittest.TestCase):
    """공통 베이스: 원본 가드 + tempfile 사본 + CLI 헬퍼.

    - setUp/tearDown 에서 원본 무결성을 검사한다.
    - copy_fixture(name) 로 깨끗한 원본의 tempfile 사본 경로를 얻는다.
    - run_cli(args, stdin) 으로 통합 CLI 를 실제 subprocess 실행한다.
    """

    def setUp(self) -> None:
        self._guard = FixtureGuard()
        self._guard.snapshot()
        self._tmpdir = tempfile.mkdtemp(prefix="gaindb_test_")

    def tearDown(self) -> None:
        shutil.rmtree(self._tmpdir, ignore_errors=True)
        # 원본이 오염되지 않았는지 마지막에 검사.
        self._guard.verify()

    def copy_fixture(self, name: str) -> str:
        """알려진 원본 음원을 tempdir 로 복사하고 사본 경로(str)를 반환.

        원본이 없으면 SkipTest. 작업은 항상 이 사본에서만 한다.
        """
        src = fixture_path(name)
        dst = Path(self._tmpdir) / src.name
        shutil.copy2(src, dst)
        return str(dst)

    def run_cli(self, args, stdin: str | None = None):
        """통합 CLI(mp3gain_cli.py)를 실제 subprocess 로 실행.

        반환: subprocess.CompletedProcess (returncode/stdout/stderr).
        인코딩은 UTF-8 고정(9항목 PowerShell 인코딩 함정 회피).
        """
        if not CLI_SCRIPT.is_file():
            raise unittest.SkipTest(f"CLI not found: {CLI_SCRIPT}")
        cmd = [sys.executable, str(CLI_SCRIPT), *map(str, args)]
        return subprocess.run(
            cmd,
            cwd=str(REPO_ROOT),
            input=stdin,
            capture_output=True,
            text=True,
            encoding="utf-8",
        )

    def audio_body_sha256(self, path: str) -> str:
        """오디오 본문(태그 제외) 해시.

        무손실 검증은 전체 해시가 아니라 tag_offset 까지의 본문 해시로 한다
        (11항목: undo 0 태그가 남아 전체 해시는 달라질 수 있음).
        """
        from gaindb.tag import read_mp3gain_ape_tag
        _info, file_tags = read_mp3gain_ape_tag(path)
        offset = file_tags.tag_offset
        h = hashlib.sha256()
        with open(path, "rb") as f:
            h.update(f.read(offset))
        return h.hexdigest()
