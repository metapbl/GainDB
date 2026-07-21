"""gui/workers.py — 백그라운드 워커(QThread) 계층. (진단 로그 임시 삽입본)"""

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


def _dlog(msg):  # DEBUGLOG
    try:
        with open("debug.log", "a", encoding="utf-8") as f:
            f.write(msg + "\n")
    except Exception:
        pass


class TagScanWorker(QThread):
    current = Signal(str)
    progress = Signal(int, int)
    row_done = Signal(str, dict)
    done = Signal()

    def __init__(self, paths, target_db, parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def run(self):
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
    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths, target_db, parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def run(self):
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
    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_analyzed = Signal(str, dict)
    row_applied = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths, target_db, seed_results, parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._target_db = target_db
        self._seed = dict(seed_results)
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def _ensure_analysis(self, path):
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

    def run(self):
        from gaindb.writer import GainCancelled

        _dlog("TRACK_APPLY_RUN_START n=" + str(len(self._paths)))  # DEBUGLOG
        total = len(self._paths)
        done = 0
        for path in self._paths:
            if self._cancel:
                break
            self.current.emit(path)
            try:
                result = self._ensure_analysis(path)
                _dlog("TRACK_ENSURE " + path + " status=" + str(result.get("status")))  # DEBUGLOG

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
                _dlog("TRACK_APPLY " + path + " status=" + str(status) + " steps=" + str(apply_res.get("steps")) + " tag_written=" + str(apply_res.get("tag_written")))  # DEBUGLOG
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
    current = Signal(str)
    progress = Signal(int, int)
    row_undone = Signal(str, int)
    row_tags_removed = Signal(str)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, paths, action, use_id3=False, parent=None):
        super().__init__(parent)
        self._paths = list(paths)
        self._action = action
        self._use_id3 = use_id3
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def run(self):
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
    current = Signal(str)
    progress = Signal(int, int)
    file_progress = Signal(float)
    row_done = Signal(str, dict)
    row_raw = Signal(str, dict)
    album_done = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, groups, target_db, parent=None):
        super().__init__(parent)
        self._groups = {k: list(v) for k, v in groups.items()}
        self._target_db = target_db
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def run(self):
        _dlog("ALBUM_RUN_START groups=" + repr(list(self._groups.keys())))  # DEBUGLOG
        total = sum(len(v) for v in self._groups.values())
        done = 0
        try:
            for key, paths in self._groups.items():
                if self._cancel:
                    break
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
                        _dlog("RAW_OK " + path + " track_db=" + repr(raw.get("track_db")) + " hist=" + str(len(raw.get("histogram") if raw.get("histogram") is not None else [])))  # DEBUGLOG
                        raws.append(raw)
                        self.row_raw.emit(path, raw)
                    except DecodeCancelled:
                        raise
                    except Exception as exc:
                        _dlog("ROW_EXC " + path + " " + repr(exc))  # DEBUGLOG
                        self.failed.emit(path, str(exc))
                    done += 1
                    self.progress.emit(done, total)

                if self._cancel or not raws:
                    continue

                agg = album_gain_from_files(raws)
                _dlog("AGG key=" + str(key) + " status=" + str(agg.get("status")) + " album_db=" + repr(agg.get("album_db")) + " n=" + str(len(raws)))  # DEBUGLOG
                if agg.get("status") != "ok":
                    for raw in raws:
                        self.failed.emit(raw["path"], "Not enough samples in album.")
                    continue
                self.album_done.emit(key, agg)

                album_db = agg["album_db"]
                for raw in raws:
                    track_res = result_from_album_raw(raw, self._target_db)
                    if track_res.get("status") != "ok":
                        _dlog("TRACK_RES_SKIP " + raw["path"] + " status=" + str(track_res.get("status")))  # DEBUGLOG
                        continue
                    shown = compute_album_display(track_res, album_db, self._target_db)
                    _dlog("ROW_EMIT " + raw["path"] + " album_db=" + repr(shown.get("album_db")))  # DEBUGLOG
                    self.row_done.emit(raw["path"], shown)
        except DecodeCancelled:
            pass
        except Exception as _exc:
            _dlog("RUN_FATAL " + repr(_exc))  # DEBUGLOG
        self.done.emit()


class AlbumApplyWorker(QThread):
    current = Signal(str)
    progress = Signal(int, int)         # 분석 구간: 진행바+카운트
    apply_progress = Signal(int, int)   # 적용 구간: 카운트만(진행바 유지)
    file_progress = Signal(float)
    row_applied = Signal(str, dict)
    row_analyzed = Signal(str, dict)
    failed = Signal(str, str)
    done = Signal()

    def __init__(self, groups, target_db, seed_raws, parent=None):
        super().__init__(parent)
        self._groups = {k: list(v) for k, v in groups.items()}
        self._target_db = target_db
        self._seed = dict(seed_raws)
        self._cancel = False

    def request_cancel(self):
        self._cancel = True

    @property
    def was_cancelled(self):
        return self._cancel

    def _ensure_group_raws(self, paths, count_state):
        _dlog("ENSURE_GROUP n_paths=" + str(len(paths)))  # DEBUGLOG
        raws = {}
        for path in paths:
            if self._cancel:
                _dlog("ENSURE_CANCEL at " + path)  # DEBUGLOG
                break
            seed = self._seed.get(path)
            if seed and "histogram" in seed:
                _dlog("ENSURE_SEED_HIT " + path)  # DEBUGLOG
                raws[path] = seed
                continue
            _dlog("ENSURE_ANALYZE " + path)  # DEBUGLOG
            self.current.emit(path)
            raw = analyze_album_file(
                path,
                should_cancel=lambda: self._cancel,
                on_progress=self.file_progress.emit,
            )
            raws[path] = raw
            # 분석 구간에서 카운트+progress 를 센다(진행바 base 갱신). 씨앗
            # 재사용 곡(위 continue)은 분석이 없어 여기 안 옴 -> 그 경우 진행바가
            # 잠깐 0 에 머물다 완료되는 게 의도된 동작.
            count_state[0] += 1
            self.progress.emit(count_state[0], count_state[1])
        _dlog("ENSURE_DONE got=" + str(len(raws)) + " of " + str(len(paths)))  # DEBUGLOG
        return raws

    def run(self):
        from gaindb.writer import GainCancelled

        _dlog("ALBUM_APPLY_RUN_START groups=" + repr(list(self._groups.keys())))  # DEBUGLOG
        total = sum(len(v) for v in self._groups.values())
        count_state = [0, total]
        try:
            for key, paths in self._groups.items():
                if self._cancel:
                    break
                _dlog("GROUP_START key=" + str(key) + " n=" + str(len(paths)))  # DEBUGLOG
                raws = self._ensure_group_raws(paths, count_state)
                _dlog("GROUP_RAWS got=" + str(len(raws)) + " cancel=" + str(self._cancel))  # DEBUGLOG
                if self._cancel or not raws:
                    _dlog("GROUP_SKIP (cancel or empty)")  # DEBUGLOG
                    continue

                agg = album_gain_from_files(list(raws.values()))
                _dlog("APPLY_AGG key=" + str(key) + " status=" + str(agg.get("status")))  # DEBUGLOG
                if agg.get("status") != "ok":
                    for path in raws:
                        self.failed.emit(path, "Not enough samples in album.")
                    continue

                album_db = agg["album_db"]
                album_peak = agg["album_peak"]
                album_min = agg["album_min"]
                album_max = agg["album_max"]

                # 적용 구간 진행을 다시 1부터 세기 위해 카운트 리셋
                # (분석 1~N, 적용 1~N 두 번 왕복). 분모는 곡 수 그대로.
                count_state[0] = 0
                _dlog("APPLY_LOOP n_raws=" + str(len(raws)))  # DEBUGLOG
                for path, raw in raws.items():
                    if self._cancel:
                        _dlog("APPLY_LOOP_CANCEL at " + path)  # DEBUGLOG
                        break
                    self.current.emit(path)
                    _dlog("APPLY_TRY " + path)  # DEBUGLOG
                    try:
                        apply_res = apply_file_album_gain(
                            path, album_db, album_peak, album_min, album_max,
                            track_seed=raw, target_db=self._target_db,
                            should_cancel=lambda: self._cancel,
                        )
                        track_res = result_from_album_raw(raw, self._target_db)
                        steps = apply_res.get("steps") or 0
                        if track_res.get("status") == "ok":
                            shown = compute_album_display(track_res, album_db, self._target_db)
                            shown = shift_after_apply(shown, steps)
                        else:
                            shown = track_res
                        _dlog("ALBUM_APPLY " + path + " status=" + str(apply_res.get("status")) + " steps=" + str(apply_res.get("steps")) + " tag_written=" + str(apply_res.get("tag_written")))  # DEBUGLOG
                        if apply_res.get("status") == "ok":
                            self.row_applied.emit(path, shown)
                        else:
                            self.row_analyzed.emit(path, shown)
                    except (DecodeCancelled, GainCancelled):
                        raise
                    except Exception as exc:
                        _dlog("APPLY_ROW_EXC " + path + " " + repr(exc))  # DEBUGLOG
                        self.failed.emit(path, str(exc))
                    count_state[0] += 1
                    self.apply_progress.emit(count_state[0], count_state[1])
        except (DecodeCancelled, GainCancelled):
            pass
        except Exception as _exc:
            _dlog("APPLY_RUN_FATAL " + repr(_exc))  # DEBUGLOG
        self.done.emit()

