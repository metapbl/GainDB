"""gui/workers.py — 백그라운드 워커(QThread) 계층.

무거운 작업(ffmpeg 디코딩 + ReplayGain 분석 + 게인 적용)을 UI 스레드에서
떼어낸다. 워커는 gaindb.api 의 순수/적용 함수만 호출하고 결과를 시그널로만
방출한다 — Qt 모델을 직접 건드리지 않는다(모델 변경은 메인 스레드 슬롯의 책임).

취소: analyze_file/analyze_album_file 에 should_cancel 을 넘겨 decode 계층이
청크 경계마다 취소를 확인하고 진행 중 ffmpeg 를 즉시 kill 한다. 취소 시
DecodeCancelled(분석)/GainCancelled(적용)가 전파되며, 워커는 이를 실패가 아닌
정상 취소로 구분한다.

파일 내부 진행률: on_progress 콜백으로 파일 내부 진행률(0~1)을 file_progress
시그널로 방출한다(분석 단계 전담, 적용은 생략).

Album 워커(AlbumAnalyzeWorker/AlbumApplyWorker)는 그룹(폴더=앨범 또는 전체)
단위로 동작한다. 그룹의 곡을 하나씩 스트리밍 분석해 원재료를 모으고,
album_gain_from_files 로 앨범 dB 를 산출한 뒤, 그룹 각 곡에 표시(analyze) 또는
적용(apply)한다. Track 워커와 시그널 인터페이스를 맞춰 메인 슬롯을 공유한다.
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
    analyze_album_file,
    album_gain_from_files,
    compute_album_display,
    apply_file_album_gain,
    result_from_album_raw,
)
from gaindb.decode import DecodeCancelled


class TagScanWorker(QThread):
    """주어진 경로들의 mp3gain 태그만 읽어 표시값을 채우는 워커(가볍다).

    디코딩이 없어 곡당 ~1ms. 파일은 변경하지 않는다(읽기 전용). 태그 읽기
    실패는 조용히 건너뛴다(pending 으로 남아 나중에 분석 대상).
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
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)
            try:
                result = read_file_tags(path, self._target_db)
                self.row_done.emit(path, result)
            except Exception:
                pass
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class AnalyzeWorker(QThread):
    """주어진 경로들을 파일별로 analyze_file 로 분석하는 워커."""

    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths: list[str], target_db: float, parent=None) -> None:
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)
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
                break
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class ApplyWorker(QThread):
    """Track Gain 을 실제 적용하는 워커(원본 RadioGain 동작 재현)."""

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
        self._seed = dict(seed_results)
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def _ensure_analysis(self, path: str):
        seed = self._seed.get(path)
        if seed and seed.get("status") == "ok" and seed.get("track_db") is not None:
            if seed.get("target_db") != self._target_db:
                return recompute_target(seed, self._target_db)
            return seed
        return analyze_file(
            path, self._target_db,
            should_cancel=lambda: self._cancel,
            on_progress=self.file_progress.emit,
        )

    def run(self) -> None:
        from gaindb.writer import GainCancelled

        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)
            try:
                result = self._ensure_analysis(path)

                if result.get("status") != "ok":
                    self.failed.emit(path, "Not enough samples to analyze.")
                    done += 1
                    self.progress.emit(done, total)
                    continue

                apply_res = apply_file_track_gain(
                    path, self._target_db, seed=result,
                    should_cancel=lambda: self._cancel,
                )
                status = apply_res.get("status")
                if status == "ok":
                    applied_steps = apply_res.get("steps") or 0
                    shown = shift_after_apply(result, applied_steps)
                    self.row_applied.emit(path, shown)
                elif status == "no_change":
                    self.row_analyzed.emit(path, result)
                else:
                    self.failed.emit(path, "Not enough samples to analyze.")
            except (DecodeCancelled, GainCancelled):
                break
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class FileActionWorker(QThread):
    """undo·태그 제거를 파일별로 수행하는 워커(원본 DoFileAction 대응)."""

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
        self._action = action
        self._use_id3 = use_id3
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)
            try:
                if self._action == "undo":
                    res = undo_file_gain(path, use_id3=self._use_id3)
                    if res.get("status") == "ok":
                        self.row_undone.emit(path, res.get("undo_steps", 0))
                    elif res.get("status") == "nothing_to_undo":
                        self.failed.emit(path, "No changes to undo.")
                    else:
                        self.failed.emit(path, "No undo information in file.")
                else:
                    remove_file_tags(path, use_id3=self._use_id3)
                    self.row_tags_removed.emit(path)
            except Exception as exc:
                self.failed.emit(path, str(exc))
            done += 1
            self.progress.emit(done, total)
        self.done.emit()


class AlbumAnalyzeWorker(QThread):
    """Album Analysis 워커(원본 Album/SingleAlbum 재현).

    그룹(폴더=앨범 또는 전체) 단위로: 그룹 곡을 하나씩 analyze_album_file 로
    스트리밍 분석해 원재료(히스토그램·peak·min/max·track_db)를 모으고, 그룹이
    끝나면 album_gain_from_files 로 앨범 dB·peak·min/max 를 산출한다. 그 뒤 그룹
    각 곡의 원재료로 track 표시 result 를 만들고(result_from_album_raw)
    compute_album_display 로 album 키를 얹어 row_done 으로 방출한다.

    파일은 변경하지 않는다(분석만). 진행 분모는 전체 곡 수(그룹 무관 합계).
    그룹 전체가 not_enough_samples 면 그 그룹 곡들을 failed 로 방출하고 넘어간다.

    입력 groups: {album_key: [path, ...]}. 메인이 group_by_album 으로 만든다.
    seed 로 곡별 원재료(raw dict)를 함께 방출해(row_done 의 result 안에는 표시
    값만 담기므로), 이후 Album Gain 이 재분석 없이 재사용할 수 있게 별도
    row_raw 시그널로도 원재료를 흘려보낸다.

    시그널:
      current(path)            : 각 곡 분석 직전 방출.
      progress(done, total)    : 곡 하나 분석이 끝날 때마다(전체 기준).
      file_progress(fraction)  : 현재 곡의 디코딩 내부 진행률(0~1).
      row_done(path, result)   : 앨범 표시(album_* 포함) result 방출.
      row_raw(path, raw)       : 곡 원재료(히스토그램 포함) 방출(Gain 재사용용).
      album_done(key, agg)     : 한 그룹의 앨범 집계(dB·peak·min/max) 방출.
      failed(path, msg)        : 곡 분석/그룹 실패 시 방출.
      done()                   : 전체 종료(취소 포함).
    """

    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_done = Signal(str, dict)
    row_raw = Signal(str, dict)
    album_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, groups: dict, target_db: float, parent=None) -> None:
        super().__init__(parent)
        # {album_key: [path,...]}. dict 순서(입력 순)를 보존해 순회한다.
        self._groups = {k: list(v) for k, v in groups.items()}
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def run(self) -> None:
        total = sum(len(v) for v in self._groups.values())
        done = 0
        try:
            for key, paths in self._groups.items():
                if self._cancel:
                    break
                # --- 그룹 곡을 하나씩 스트리밍 분석해 원재료 수집 ---
                raws = []
                for path in paths:
                    if self._cancel:
                        break
                    self.current.emit(path)
                    try:
                        raw = analyze_album_file(
                            path,
                            should_cancel=lambda: self._cancel,
                            on_progress=self.file_progress.emit,
                        )
                        raws.append(raw)
                        self.row_raw.emit(path, raw)
                    except DecodeCancelled:
                        # 취소: 바깥 루프까지 빠져나간다.
                        raise
                    except Exception as exc:
                        self.failed.emit(path, str(exc))
                    done += 1
                    self.progress.emit(done, total)

                if self._cancel or not raws:
                    continue

                # --- 그룹 앨범 집계 ---
                agg = album_gain_from_files(raws)
                if agg.get("status") != "ok":
                    # 그룹 전체 not_enough: 곡들을 실패로 알린다.
                    for raw in raws:
                        self.failed.emit(
                            raw["path"], "Not enough samples in album.")
                    continue
                self.album_done.emit(key, agg)

                # --- 그룹 각 곡의 표시 result 생성(track + album) ---
                album_db = agg["album_db"]
                for raw in raws:
                    track_res = result_from_album_raw(raw, self._target_db)
                    if track_res.get("status") != "ok":
                        # track 표시를 못 만드는 곡은 그대로 둔다(합의된 단순화).
                        continue
                    shown = compute_album_display(
                        track_res, album_db, self._target_db)
                    self.row_done.emit(raw["path"], shown)
        except DecodeCancelled:
            pass  # 취소는 정상 종료.
        self.done.emit()


class AlbumApplyWorker(QThread):
    """Album Gain 을 실제 적용하는 워커(원본 AlbumGain 재현).

    그룹 단위로: 씨앗(seed_raws)이 있으면 재분석 없이 album_gain_from_files 로
    앨범 dB 를 산출하고(원재료 재사용), 없으면 analyze_album_file 로 먼저 분석
    한다. 그 뒤 그룹 각 곡에 apply_file_album_gain 을 호출해 그룹 공통 스텝을
    적용하며 track+album 태그를 둘 다 기록한다.

    진행률은 Track 정책 준용: 분석 단계만 file_progress 로 표시하고 적용은
    생략(적용은 프레임 순회라 순식간). 취소는 청크(분석)·프레임(적용) 경계.

    입력 groups: {album_key: [path,...]}.
    seed_raws: {path: analyze_album_file 원재료}. Album Analysis 로 이미 확보한
      원재료를 재사용해 재디코딩을 막는다(이중 디코딩 제거). 없으면 그 그룹을
      다시 분석한다.

    시그널:
      current(path)             : 각 곡 처리 직전.
      progress(done, total)     : 곡 하나 처리가 끝날 때마다(전체 기준).
      file_progress(fraction)   : 분석 단계 파일 내부 진행률.
      row_applied(path, result) : 적용된 곡의 표시(album_* 포함) result.
      row_analyzed(path, result): steps==0 으로 적용 안 한 곡의 표시 result.
      failed(path, msg)         : 곡/그룹 실패 시.
      done()                    : 전체 종료(취소 포함).

    파일을 실제로 변경한다(파괴적).
    """

    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_applied = Signal(str, dict)
    row_analyzed = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, groups: dict, target_db: float,
                 seed_raws: dict, parent=None) -> None:
        super().__init__(parent)
        self._groups = {k: list(v) for k, v in groups.items()}
        self._target_db = target_db
        self._seed = dict(seed_raws)  # {path: raw dict}
        self._cancel = False

    def request_cancel(self) -> None:
        self._cancel = True

    @property
    def was_cancelled(self) -> bool:
        return self._cancel

    def _ensure_group_raws(self, paths, count_state):
        """그룹의 곡별 원재료를 확보한다(씨앗 재사용 또는 분석).

        count_state: [done, total] 리스트(진행 방출용, 가변 참조로 갱신).
        분석한 곡은 progress 를 방출한다(씨앗 재사용 곡은 분석이 없어 방출 안 함).
        반환: {path: raw}. 취소 시 DecodeCancelled 전파.
        """
        raws = {}
        for path in paths:
            if self._cancel:
                break
            seed = self._seed.get(path)
            if seed and "histogram" in seed:
                raws[path] = seed
                continue
            # 씨앗 없음: 지금 분석(무겁다).
            self.current.emit(path)
            raw = analyze_album_file(
                path,
                should_cancel=lambda: self._cancel,
                on_progress=self.file_progress.emit,
            )
            raws[path] = raw
            count_state[0] += 1
            self.progress.emit(count_state[0], count_state[1])
        return raws

    def run(self) -> None:
        from gaindb.writer import GainCancelled

        total = sum(len(v) for v in self._groups.values())
        # 진행 분모: 분석(씨앗 없는 곡) + 적용(모든 곡). 씨앗이 다 있으면 적용만.
        # 단순화를 위해 분모를 전체 곡 수로 두고, 적용 완료를 기준으로 센다.
        count_state = [0, total]
        try:
            for key, paths in self._groups.items():
                if self._cancel:
                    break

                # --- 그룹 원재료 확보(씨앗 재사용 또는 분석) ---
                raws = self._ensure_group_raws(paths, count_state)
                if self._cancel or not raws:
                    continue

                # --- 그룹 앨범 집계 ---
                agg = album_gain_from_files(list(raws.values()))
                if agg.get("status") != "ok":
                    for path in raws:
                        self.failed.emit(path, "Not enough samples in album.")
                    continue

                album_db = agg["album_db"]
                album_peak = agg["album_peak"]
                album_min = agg["album_min"]
                album_max = agg["album_max"]

                # --- 그룹 각 곡에 앨범 게인 적용 ---
                for path, raw in raws.items():
                    if self._cancel:
                        break
                    self.current.emit(path)
                    try:
                        apply_res = apply_file_album_gain(
                            path, album_db, album_peak, album_min, album_max,
                            track_seed=raw, target_db=self._target_db,
                            should_cancel=lambda: self._cancel,
                        )
                        # 표시 result: track + album, 적용 스텝만큼 이동.
                        track_res = result_from_album_raw(raw, self._target_db)
                        steps = apply_res.get("steps") or 0
                        if track_res.get("status") == "ok":
                            shown = compute_album_display(
                                track_res, album_db, self._target_db)
                            shown = shift_after_apply(shown, steps)
                        else:
                            shown = track_res
                        if apply_res.get("status") == "ok":
                            self.row_applied.emit(path, shown)
                        else:  # no_change
                            self.row_analyzed.emit(path, shown)
                    except (DecodeCancelled, GainCancelled):
                        raise
                    except Exception as exc:
                        self.failed.emit(path, str(exc))
                    count_state[0] += 1
                    self.progress.emit(count_state[0], count_state[1])
        except (DecodeCancelled, GainCancelled):
            pass
        self.done.emit()
