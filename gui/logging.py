# SPDX-License-Identifier: Apache-2.0
# SPDX-FileCopyrightText: 2026 META PUBLIC
r"""gui/logging.py — 로그 파일 기록(독립 구현).

세 종류의 로그를 파일에 append 한다(관찰된 동작만 차용):
  - Error Log:    처리 중 오류를 남긴다.
  - Analysis Log: 분석 결과(TrackdB/MaxAmp, AlbumdB)를 남긴다.
  - Change Log:   실제 게인 변경 내역을 남긴다.

mp3gain 과의 확정된 차이(합의, CLAUDE.md 10.2):
  - 켜기/끄기 UX: 원래 동작은 숨겨진 체크박스 + "경로 유무"로 판정하나, 우리는
    그 체크박스를 노출해 on/off(enabled)와 위치(path)를 분리한다(A안). enabled
    이면서 path 가 있을 때만 기록한다(체크됐는데 경로 없으면 조용히 no-op).
  - dB 표기 상수: 화면 근사값 1.505 대신 정본 정밀값 FIVELOG10TWO(=5*log10(2))로
    통일한다(db_to_steps 정밀값 정책과 일관).
  - 타임스탬프: 로케일 의존 형식은 재현 대상으로 부적절하므로, 로케일 무관
    ISO 8601 고정 형식("YYYY-MM-DD HH:MM:SS")으로 대체한다.

이 모듈은 순수 파일 I/O 로 Qt 에 의존하지 않는다(tests 에서 원본 음원·ffmpeg·
Qt 없이 검증 가능). 파일 쓰기 실패는 삼키지 않고 LogWriteError 로 올려 호출자
(GUI)가 상태바로 안내하게 한다. append 는 UTF-8.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

# 1 스텝당 dB(정본 정밀값 5*log10(2)). 화면 근사 1.505 대신 이 값을 써
# 프로젝트 dB 표기를 db_to_steps 정밀값 정책과 통일한다(10.2).
FIVELOG10TWO = 1.50514997831991


class LogWriteError(Exception):
    """로그 파일을 열거나 쓸 수 없을 때 올린다."""


@dataclass
class LogConfig:
    """세 로그의 on/off 와 경로를 담는 홀더.

    각 로그는 enabled 이면서 path 가 비어있지 않을 때만 기록한다. 체크박스를
    껐다 켜도 경로가 유지되도록 on/off 와 path 를 분리해서 보관한다(A안).
    """

    error_enabled: bool = False
    error_path: str = ""
    analysis_enabled: bool = False
    analysis_path: str = ""
    change_enabled: bool = False
    change_path: str = ""

    def error_active(self) -> bool:
        return bool(self.error_enabled and self.error_path)

    def analysis_active(self) -> bool:
        return bool(self.analysis_enabled and self.analysis_path)

    def change_active(self) -> bool:
        return bool(self.change_enabled and self.change_path)


def _timestamp() -> str:
    """로케일 무관 ISO 8601 타임스탬프(초 단위)."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def _append_line(path: str, line: str) -> None:
    """path 파일 끝에 line + 개행을 UTF-8 로 덧붙인다.

    실패(권한·경로 없음 등)는 LogWriteError 로 올린다. 호출자는 활성 상태를
    먼저 확인하므로 여기서는 path 가 비어있지 않다고 가정한다.
    """
    try:
        with open(path, "a", encoding="utf-8") as fh:
            fh.write(line + "\n")
    except OSError as exc:
        raise LogWriteError(str(exc)) from exc


def check_writable(path: str) -> bool:
    """path 를 append 모드로 열 수 있는지 검사한다.

    파일이 없으면 만들어질 수 있는지까지 포함해 확인한다(append 는 없으면 생성).
    성공하면 True, 실패하면 False. 다이얼로그 OK 검증에서 쓴다.
    """
    if not path:
        return False
    try:
        with open(path, "a", encoding="utf-8"):
            pass
        return True
    except OSError:
        return False


def _fmt_db(steps: int) -> str:
    """스텝 수를 dB 문자열로(정밀값 × steps, 소수 첫째자리)."""
    return format(steps * FIVELOG10TWO, ".1f")


def log_error(cfg: LogConfig, message: str) -> None:
    """오류 한 건을 Error Log 에 남긴다(형식: ts<TAB>message).

    로그가 비활성이면 아무 것도 하지 않는다(no-op).
    """
    if not cfg.error_active():
        return
    _append_line(cfg.error_path, f"{_timestamp()}\t{message}")


def log_analysis_track(cfg: LogConfig, path: str,
                       track_db: float, max_amp: float) -> None:
    """Track 분석 결과를 Analysis Log 에 남긴다.

    형식: ts<TAB>path<TAB>TrackdB: <db><TAB>MaxAmp: <amp>
    max_amp 는 정수(진폭)로 반올림해 표기.
    """
    if not cfg.analysis_active():
        return
    line = (f"{_timestamp()}\t{path}\t"
            f"TrackdB: {track_db}\tMaxAmp: {int(round(max_amp))}")
    _append_line(cfg.analysis_path, line)


def log_analysis_album(cfg: LogConfig, path: str, album_db: float) -> None:
    """Album 분석 결과를 Analysis Log 에 남긴다.

    형식: ts<TAB>path<TAB>AlbumdB: <db>
    """
    if not cfg.analysis_active():
        return
    _append_line(cfg.analysis_path,
                 f"{_timestamp()}\t{path}\tAlbumdB: {album_db}")


def log_change(cfg: LogConfig, path: str, steps: int) -> None:
    """게인 변경 한 건을 Change Log 에 남긴다.

    형식: ts<TAB>path<TAB><db>  (db = steps × FIVELOG10TWO, 소수 첫째자리)
    steps==0 이면(실질 변경 없음) 기록하지 않는다.
    """
    if not cfg.change_active() or not steps:
        return
    _append_line(cfg.change_path, f"{_timestamp()}\t{path}\t{_fmt_db(steps)}")