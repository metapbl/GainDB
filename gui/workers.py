"""gui/workers.py — 백그라운드 워커(QThread) 계층.

무거운 작업(ffmpeg 디코딩 + ReplayGain 분석 + 게인 적용)을 UI 스레드에서
떼어낸다. 워커는 gaindb.api 의 순수/적용 함수만 호출하고 결과를 시그널로만
방출한다 — Qt 모델을 직접 건드리지 않는다(모델 변경은 메인 스레드 슬롯의 책임).

취소(정책 갱신):
  예전에는 취소를 파일 경계에서만 반영했으나(진행 중 ffmpeg 방치), 초장시간
  곡(수 시간)에서는 그 한 곡이 끝날 때까지 취소가 먹히지 않아 UI 가 굳은 것
  처럼 보였다. 이제 워커는 analyze_file 에 should_cancel 콜백을 넘겨, decode
  계층이 청크 경계마다 취소를 확인하고 진행 중 ffmpeg 를 즉시 kill 한다. 취소
  시 decode 는 DecodeCancelled(=DecodeError 하위)를 던지며, 워커는 이를 실패
  (failed)가 아니라 정상 취소로 구분해 조용히 루프를 빠져나온다. 취소는 여전히
  '청크 경계'라 즉시는 아니지만 수백 ms 이내로 반영된다.

파일 내부 진행률:
  긴 곡 디코딩 중에도 UI 가 살아있음을 보이도록, 워커는 analyze_file 에
  on_progress 콜백을 넘겨 파일 내부 진행률(0~1)을 file_progress 시그널로
  방출한다. 메인 창이 이를 상태바 텍스트("파일명 — NN.N%")와 진행바 세분
  합산에 쓴다. duration 기반 근사라 완료 시 1.0 으로 마무리된다.

각 워커는 파일 처리 직전에 current(path) 를 방출한다 — 메인 창이 상태바에
"지금 처리 중인 파일명"을 보여주는 데 쓴다(경로 없이 basename 만 표시).

태그 스캔(TagScanWorker)만은 성격이 다르다: 디코딩 없이 파일 꼬리 태그만
읽으므로 곡당 매우 가볍고(~1ms), 취소는 사실상 즉시 반영된다. 대량 추가 시
UI 프리징을 없애기 위해 추가 흐름에서 이 워커로 태그를 백그라운드로 채운다.
태그 스캔의 "취소"는 완전 취소가 아니라 일시 중단(Pause)이며, 멈춘 뒤 남은
행은 Rescan 으로 이어서 스캔한다(메인 창이 pending 행을 다시 넘긴다). 태그
스캔은 디코딩이 없어 파일 내부 진행률이 무의미하므로 file_progress 를 쓰지
않는다(시그널은 인터페이스 통일을 위해 정의만 둔다).

파일 액션(FileActionWorker)도 태그 스캔처럼 가볍다: undo·태그 제거는 디코딩
없이 태그·프레임 게인만 건드린다(원본 DoFileAction → UndoFileGain/DeleteFileTags
대응). 하나의 워커가 action("undo"|"remove_tags")으로 분기해, 원본이 공통
껍데기(DoFileAction) + 종류별 함수로 나눈 구조를 그대로 따른다. 취소는 파일
경계에서 반영된다(각 곡이 빠르므로 실질 문제 없음).
"""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from gaindb.api import (
    analyze_file,
    apply_file_track_gain,
    read_file_tags,
    recompute_target,
    shift_after_apply,
    undo_file_gain,
    remove_file_tags,
)
from gaindb.decode import DecodeCancelled


class TagScanWorker(QThread):
    """주어진 경로들의 mp3gain 태그만 읽어 표시값을 채우는 워커(가볍다).

    원본 MP3GainGUI AddSingleFile 의 `/o /s c` 태그 조회에 대응한다. 디코딩이
    없어 곡당 ~1ms. 대량 추가 시 메인 스레드가 이걸 순차로 돌면 UI 가 몇 분
    프리징되므로 백그라운드로 옮긴다. 파일은 변경하지 않는다(읽기 전용).

    시그널:
      current(path)         : 각 파일 처리 직전 방출(상태바 "처리 중" 표시용).
      progress(done, total) : 한 파일 처리가 끝날 때마다 방출.
      row_done(path, result): 태그 조회 성공 시 결과 dict 와 함께 방출.
                              (result["status"] 는 "ok" 또는 "no_tag" — 둘 다
                              정상 흐름이라 failed 가 아니라 row_done 으로 보낸다.)
      done()                : 전체 종료(Pause 포함).

    태그 읽기 중 진짜 예외(파일 손상 등)는 조용히 건너뛴다(원래 _add_from 도
    태그 실패를 무시했음). 그런 행은 pending 으로 남아 나중에 분석 대상이 된다.
    """

    current = Signal(str)
    progress = Signal(int, int)
    row_done = Signal(str, dict)
    done = Signal()

    def __init__(self, paths: list[str], target_db: float, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self) -> None:
        """파일 경계에서 멈추도록 중단(Pause)을 요청한다."""
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        """중단(Pause) 요청이 들어온 채로 종료됐는지. 완료 슬롯의 메시지 분기용."""
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)  # 상태바 "처리 중" 표시용(처리 직전).
            try:
                result = read_file_tags(path, self._target_db)
                self.row_done.emit(path, result)
            except Exception:
                # 태그 읽기 실패는 치명적이지 않다. pending 으로 남겨 넘어간다.
                pass
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class AnalyzeWorker(QThread):
    """주어진 경로들을 파일별로 analyze_file 로 분석하는 워커.

    시그널:
      current(path)              : 각 파일 처리 직전 방출(상태바 "처리 중" 표시).
      progress(done, total)      : 한 파일 처리가 끝날 때마다 방출(성공/실패 무관).
      file_progress(fraction)    : 현재 파일의 디코딩 내부 진행률(0~1). 긴 곡에서
                                   진행 상황을 보이려 청크마다 방출한다.
      row_done(path, result)     : 분석 성공 시 결과 dict 와 함께 방출.
      failed(path, msg)          : 분석 중 (취소가 아닌) 예외 발생 시 방출.
      done()                     : 전체 종료(취소 포함). QThread 기본 finished 와
                                   구분해 명시적으로 방출한다.
    """

    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()  # 자체 완료 시그널(QThread.finished 와 이름 충돌 회피)

    def __init__(self, paths: list[str], target_db: float, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self) -> None:
        """청크 경계에서 멈추도록 취소를 요청한다(스레드 안전한 플래그 설정).

        decode 계층이 이 플래그를 콜백으로 받아 청크마다 확인하고, 서면 진행
        중 ffmpeg 를 kill 하고 DecodeCancelled 를 던진다.
        """
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        """취소 요청이 들어온 채로 종료됐는지. 완료 슬롯의 메시지 분기에 쓴다."""
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)  # 상태바 "처리 중" 표시용(처리 직전).
            try:
                result = analyze_file(
                    path, self._target_db,
                    should_cancel=lambda: self._cancel,
                    on_progress=self.file_progress.emit,
                )
                if result.get("status") == "not_enough_samples":
                    self.failed.emit(path, "Not enough samples to analyze.")
                else:
                    self.row_done.emit(path, result)
            except DecodeCancelled:
                # 취소는 실패가 아니다. 루프를 빠져나가 done 으로 마무리한다.
                break
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
      2) 확보한 result 를 씨앗으로 apply_file_track_gain 에 넘겨 적용한다.
         씨앗이 유효하면(track_db·peak 보유) 코어가 디코딩·분석·scan 을
         건너뛴다(이중 디코딩 제거). steps==0 이면 코어가 no_change 로 넘긴다.
         (원본: /g <steps> 실행 후 AlterDb 로 dB 이동 → DispJunk)

    입력 seed_results 는 {path: 기존 result dict}. 이미 분석/태그로 값이 있는
    행은 재분석 없이 그 result 를 그대로 씨앗으로 쓴다(원본이 RadiodBGain 이
    이미 있으면 재분석하지 않는 것과 일치). target_db 가 씨앗과 다르면
    recompute_target 으로 steps 를 목표에 맞춰 다시 계산한다.

    취소·진행률(정책 갱신 — 적용 단계까지 확장):
      미분석 곡을 내부에서 분석할 때 analyze_file 에 should_cancel·on_progress
      를 넘긴다(디코딩 진행률). 그에 더해, 실제 적용 단계(scan_gain·apply_gain·
      change_gain_and_tag 의 프레임 순회)에도 같은 콜백을 넘긴다 — 초장시간
      곡에서 '분석 100% 이후' 순수 파이썬 순회에 갇혀 취소가 안 먹던 문제를
      해소한다. 취소 시 DecodeCancelled(분석 중) 또는 GainCancelled(적용 중)를
      받아 정상 종료한다. 두 예외 모두 그 시점에 파일이 원본 그대로다.

    파일 내부 진행률 매핑(한 파일 = 한 번의 0→100%):
      미분석 곡은 분석·적용 두 단계를 거치므로, 그냥 두면 file_progress 가
      0→1 을 두 번 그린다(진행바 역행처럼 보임). 그래서 워커가 단계별로 구간을
      나눠 매핑해 방출한다 — 분석은 0~_ANALYZE_SPLIT, 적용은 _ANALYZE_SPLIT~1.
      씨앗 재사용 곡은 분석 단계가 없으므로 적용을 0~1 전체로 매핑한다. 이
      매핑은 '어느 곡이 씨앗 재사용인가'(워커만 아는 정보)에 달렸으므로 워커가
      담당한다. 메인 창은 매핑된 fraction 을 세분 합산에 쓰기만 한다(무계산).

    시그널:
      current(path)             : 각 파일 처리 직전 방출(상태바 "처리 중" 표시).
      progress(done, total)     : 파일 하나 처리가 끝날 때마다 방출.
      file_progress(fraction)   : 분석+적용을 한 구간으로 합친 파일 내부 진행률.
      row_analyzed(path, result): 분석만 하고 적용 안 함(steps=0). 표시 dict.
      row_applied(path, result) : 적용까지 함. shift_after_apply 반영된 표시 dict.
      failed(path, msg)         : 분석/적용 중 (취소가 아닌) 예외 발생.
      done()                    : 전체 종료(취소 포함).

    적용은 파일을 실제로 변경한다(파괴적). 취소는 청크(분석)·프레임 순회
    간격(적용) 경계에서 수백 ms 이내 반영된다.
    """

    # 미분석 곡에서 파일 내부 진행률을 분석/적용에 배분하는 분할점.
    # 분석(디코딩)이 적용(프레임 순회 2회)보다 대체로 무거워 0.7 로 둔다.
    # 정확한 비율은 곡·환경마다 다르나, 목적(진행바가 한 방향으로만 흐름)에는
    # 어떤 고정 비율이든 충분하다. 씨앗 재사용 곡은 이 분할을 쓰지 않는다.
    _ANALYZE_SPLIT = 0.7

    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
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

    @property
    def was_cancelled(self) -> bool:
        """취소 요청이 들어온 채로 종료됐는지. 완료 슬롯의 메시지 분기에 쓴다."""
        return self._cancel

    def _seed_is_reusable(self, path: str) -> bool:
        """이 곡이 씨앗 재사용(분석 단계 생략) 대상인지.

        _ensure_analysis 의 재사용 조건과 반드시 동일해야 진행률 매핑이 실제
        실행 단계와 어긋나지 않는다(track_db 보유 = 분석 결과 유효).
        """
        seed = self._seed.get(path)
        return bool(seed and seed.get("status") == "ok"
                    and seed.get("track_db") is not None)

    def _ensure_analysis(self, path: str):
        """이 파일의 분석 result 를 확보한다(없거나 미분석이면 새로 분석).

        반환: 목표(target_db)에 맞춰 계산된 표시 result dict.
        예외(DecodeCancelled 포함)는 호출자(run)가 처리한다.
        분석 진행률은 analyze_progress 콜백(run 이 구간 매핑해 넘김)으로 방출.
        """
        seed = self._seed.get(path)
        # 씨앗이 유효한 분석 결과면(track_db 보유) 재분석 없이 재사용한다
        # (원본: RadiodBGain 이 이미 있으면 다시 분석하지 않음).
        if seed and seed.get("status") == "ok" and seed.get("track_db") is not None:
            # 목표가 씨앗과 다르면 steps 를 목표에 맞춰 다시 계산(파일 미접촉).
            if seed.get("target_db") != self._target_db:
                return recompute_target(seed, self._target_db)
            return seed
        # 미분석: 지금 분석한다(무겁다: decode+scan). 취소·진행률 콜백 전달.
        return analyze_file(
            path, self._target_db,
            should_cancel=lambda: self._cancel,
            on_progress=self._analyze_progress,
        )

    def _analyze_progress(self, fraction: float) -> None:
        """분석 단계 진행률(0~1)을 0~_ANALYZE_SPLIT 구간으로 매핑해 방출."""
        self.file_progress.emit(fraction * self._ANALYZE_SPLIT)

    def run(self) -> None:
        from gaindb.writer import GainCancelled

        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)  # 상태바 "처리 중" 표시용(처리 직전).

            # 이 곡이 씨앗 재사용인지 먼저 판정해 적용 진행률 매핑을 정한다.
            # 재사용 곡은 분석 단계가 없어 적용을 0~1 전체로, 미분석 곡은
            # 분석(0~SPLIT) 뒤라 적용을 SPLIT~1 로 매핑한다.
            reuse = self._seed_is_reusable(path)
            if reuse:
                def apply_progress(g, _emit=self.file_progress.emit):
                    _emit(g)
            else:
                def apply_progress(g, _emit=self.file_progress.emit,
                                   _split=self._ANALYZE_SPLIT):
                    _emit(_split + g * (1.0 - _split))

            try:
                result = self._ensure_analysis(path)

                if result.get("status") != "ok":
                    # not_enough_samples 등: 적용 불가.
                    self.failed.emit(path, "Not enough samples to analyze.")
                    done += 1
                    self.progress.emit(done, total)
                    continue

                # 확보한 result 를 씨앗으로 넘겨 이중 디코딩을 막는다. 적용 단계
                # 프레임 순회의 취소·진행률도 콜백으로 연결한다(100% 이후 정지·
                # 취소 불가 해소). steps 가 0 이어도 항상 호출한다(dirty 태그면
                # 코어가 태그를 다시 씀 — 원본 -r 동일).
                apply_res = apply_file_track_gain(
                    path, self._target_db, seed=result,
                    should_cancel=lambda: self._cancel,
                    on_progress=apply_progress,
                )
                status = apply_res.get("status")
                if status == "ok":
                    # 실제 게인 적용됨: 적용된 상태의 표시 dict 방출.
                    applied_steps = apply_res.get("steps") or 0
                    shown = shift_after_apply(result, applied_steps)
                    self.row_applied.emit(path, shown)
                elif status == "no_change":
                    # steps=0. 오디오 미변경(태그만 갱신됐을 수 있음).
                    self.row_analyzed.emit(path, result)
                else:
                    # not_enough_samples 등.
                    self.failed.emit(path, "Not enough samples to analyze.")
            except (DecodeCancelled, GainCancelled):
                # 취소는 실패가 아니다. 루프를 빠져나가 done 으로 마무리한다.
                break
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class FileActionWorker(QThread):
    """undo·태그 제거를 파일별로 수행하는 워커(원본 DoFileAction 대응).

    원본 MP3GainGUI 의 DoFileAction 은 공통 전후처리(진행바·취소·busy 잠금)를
    한 껍데기에 두고 가운데에서 action(taUndoGain/taDeleteTags)으로 분기해
    UndoFileGain / DeleteFileTags 를 불렀다. 이 워커도 같은 구조로, 하나의
    run 이 action("undo"|"remove_tags")으로 분기한다.

    undo·제거는 디코딩이 없어 가볍다(태그·프레임 게인만 건드림). 파일 내부
    진행률이 무의미하므로 file_progress 를 쓰지 않는다(정의도 두지 않음).
    취소는 파일 경계에서 반영된다(각 곡이 빠르므로 실질 문제 없음).

    시그널:
      current(path)              : 각 파일 처리 직전 방출(상태바 "처리 중" 표시).
      progress(done, total)      : 한 파일 처리가 끝날 때마다 방출(성공/실패 무관).
      row_undone(path, steps)    : undo 성공 시 되돌린 스텝과 함께 방출.
                                   (호출자가 shift_after_apply 로 표시 갱신)
      row_tags_removed(path)     : 태그 제거 성공 시 방출.
                                   (호출자가 clear_result 로 미분석 복귀)
      failed(path, msg)          : 처리 중 예외/불가 상황 방출(undo 정보 없음 등).
      done()                     : 전체 종료(취소 포함).

    파일을 실제로 변경한다(파괴적). action 은 생성 시 고정된다.
    """

    current = Signal(str)
    progress = Signal(int, int)
    row_undone = Signal(str, int)
    row_tags_removed = Signal(str)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths: list[str], action: str,
                 use_id3: bool = False, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._action = action          # "undo" | "remove_tags"
        self._use_id3 = use_id3
        self._cancel = False

    def request_cancel(self) -> None:
        """파일 경계에서 멈추도록 취소를 요청한다."""
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        """취소 요청이 들어온 채로 종료됐는지. 완료 슬롯의 메시지 분기에 쓴다."""
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)  # 상태바 "처리 중" 표시용(처리 직전).
            try:
                if self._action == "undo":
                    res = undo_file_gain(path, use_id3=self._use_id3)
                    if res.get("status") == "ok":
                        self.row_undone.emit(path, res.get("undo_steps", 0))
                    elif res.get("status") == "nothing_to_undo":
                        self.failed.emit(path, "No changes to undo.")
                    else:  # no_undo
                        self.failed.emit(path, "No undo information in file.")
                else:  # "remove_tags"
                    remove_file_tags(path, use_id3=self._use_id3)
                    self.row_tags_removed.emit(path)
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()
