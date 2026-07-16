"""gui/workers.py — 백그라운드 워커(QThread) 계층.

무거운 작업(ffmpeg 디코딩 + ReplayGain 분석)을 UI 스레드에서 떼어낸다.
워커는 gaindb.api 의 순수 함수만 호출하고 결과를 시그널로만 방출한다 —
Qt 모델을 직접 건드리지 않는다(모델 변경은 메인 스레드 슬롯의 책임).

취소는 파일 경계에서만 반영한다(진행 중인 ffmpeg 프로세스를 강제 중단하지
않고, 현재 파일이 끝나면 멈춘다). 파일별 예외는 워커가 잡아 failed 로 넘긴다.
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from gaindb.api import analyze_file


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
