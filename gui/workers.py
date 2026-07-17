"""gui/workers.py — 백그라운드 워커(QThread) 계층.

무거운 작업(ffmpeg 디코딩 + ReplayGain 분석 + 게인 적용)을 UI 스레드에서
떼어낸다. 워커는 gaindb.api 의 순수/적용 함수만 호출하고 결과를 시그널로만
방출한다 — Qt 모델을 직접 건드리지 않는다(모델 변경은 메인 스레드 슬롯의 책임).

취소는 파일 경계에서만 반영한다(진행 중인 ffmpeg 프로세스를 강제 중단하지
않고, 현재 파일이 끝나면 멈춘다). 파일별 예외는 워커가 잡아 failed 로 넘긴다.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from gaindb.api import (
    analyze_file,
    apply_file_track_gain,
    recompute_target,
    shift_after_apply,
)


class AnalyzeWorker(QThread):
    """주어진 경로들을 파일별로 analyze_file 로 분석하는 워커.

    시그널:
      progress(done, total) : 한 파일 처리가 끝날 때마다 방출(성공/실패 무관).
      row_done(path, result): 분석 성공 시 결과 dict 와 함께 방출.
      failed(path, msg)     : 분석 중 예외 발생 시 오류 메시지와 함께 방출.
      finished()            : 전체 종료(취소 포함). QThread 기본 finished 와
                              구분해 명시적으로 방출한다.
    """

    progress = Signal(int, int)
    row_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()  # 자체 완료 시그널(QThread.finished 와 이름 충돌 회피)

    def __init__(self, paths: list[str], target_db: float, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self) -> None:
        """파일 경계에서 멈추도록 취소를 요청한다(스레드 안전한 플래그 설정)."""
        self._cancel = True

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            try:
                result = analyze_file(path, self._target_db)
                if result.get("status") == "not_enough_samples":
                    self.failed.emit(path, "Not enough samples to analyze.")
                else:
                    self.row_done.emit(path, result)
            except Exception as exc:  # 파일 손상·ffmpeg 실패 등 → 행 오류로.
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class ApplyWorker(QThread):
    """Track Gain 을 실제 적용하는 워커(원본 RadioGain 동작 재현).

    파일별 처리(원본 RadioGain 루프 대응):
      1) 미분석이면(기존 result 없음) analyze_file 로 먼저 분석한다.
         (원본: RadiodBGain=NOREALNUM 이면 RadioSingleFile 로 분석)
      2) 그 결과의 steps 가 0 이면 적용하지 않고 분석 결과만 방출한다.
         (원본: RadioMp3Gain=0 이면 /g 를 실행하지 않고 넘어감 — "분석까지만")
      3) steps 가 0 이 아니면 apply_file_track_gain 으로 실제 적용하고,
         shift_after_apply 로 "적용된 상태"의 표시 dict 를 만들어 방출한다.
         (원본: /g <steps> 실행 후 AlterDb 로 dB 이동 → DispJunk)

    입력 seed_results 는 {path: 기존 result dict}. 이미 분석/태그로 값이 있는
    행은 재분석 없이 그 result 를 그대로 씨앗으로 쓴다(원본이 RadiodBGain 이
    이미 있으면 재분석하지 않는 것과 일치). target_db 가 씨앗과 다르면
    recompute_target 으로 steps 를 목표에 맞춰 다시 계산한다.

    시그널:
      progress(done, total)     : 파일 하나 처리가 끝날 때마다 방출.
      row_analyzed(path, result): 분석만 하고 적용 안 함(steps=0). 표시 dict.
      row_applied(path, result) : 적용까지 함. shift_after_apply 반영된 표시 dict.
      failed(path, msg)         : 분석/적용 중 예외 발생.
      done()                    : 전체 종료(취소 포함).

    적용은 파일을 실제로 변경한다(파괴적). 취소는 파일 경계에서만 반영한다.
    """

    progress = Signal(int, int)
    row_analyzed = Signal(str, dict)
    row_applied = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths: list[str], target_db: float,
                 seed_results: dict, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        # {path: result dict or None}. 얕은 참조로 충분(워커에서 수정 안 함).
        self._seed = dict(seed_results)
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    def _ensure_analysis(self, path: str):
        """이 파일의 분석 result 를 확보한다(없거나 미분석이면 새로 분석).

        반환: 목표(target_db)에 맞춰 계산된 표시 result dict.
        예외는 호출자(run)가 잡아 failed 로 넘긴다.
        """
        seed = self._seed.get(path)
        # 씨앗이 유효한 분석 결과면(track_db 보유) 재분석 없이 재사용한다
        # (원본: RadiodBGain 이 이미 있으면 다시 분석하지 않음).
        if seed and seed.get("status") == "ok" and seed.get("track_db") is not None:
            # 목표가 씨앗과 다르면 steps 를 목표에 맞춰 다시 계산(파일 미접촉).
            if seed.get("target_db") != self._target_db:
                return recompute_target(seed, self._target_db)
            return seed
        # 미분석: 지금 분석한다(무겁다: decode+scan).
        return analyze_file(path, self._target_db)

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            try:
                result = self._ensure_analysis(path)

                if result.get("status") != "ok":
                    # not_enough_samples 등: 적용 불가.
                    self.failed.emit(path, "Not enough samples to analyze.")
                    done += 1
                    self.progress.emit(done, total)
                    continue

                steps = result.get("steps") or 0
                if steps == 0:
                    # 원본: RadioMp3Gain=0 → /g 미실행, 분석까지만.
                    self.row_analyzed.emit(path, result)
                else:
                    # 원본: /g <steps> 적용 후 dB 이동. 우리는 apply 후 shift.
                    apply_res = apply_file_track_gain(path, self._target_db)
                    applied_steps = apply_res.get("steps") or 0
                    shown = shift_after_apply(result, applied_steps)
                    self.row_applied.emit(path, shown)
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()
