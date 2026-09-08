import os
import re
import stat as stat_module
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from watchdog.events import FileDeletedEvent, FileModifiedEvent, FileSystemEvent

from app.source_path_filter import PathFilter
from app.utils.logger import get_logger


logger = get_logger(__name__)

ASSIGNMENT_DIRECTORY = re.compile(r"assignment-[1-9][0-9]*")
PRUNED_DIRECTORIES = {
    "env",
    "lib",
    "lib64",
    "libs",
    "node_modules",
    "site-packages",
    "dist-packages",
}


@dataclass(frozen=True)
class FileSignature:
    mtime_ns: int
    size: int
    inode: int


def _is_pruned_directory(name: str) -> bool:
    return name.startswith(".") or name.lower() in PRUNED_DIRECTORIES


def _assignment_directories(watch_root: Path) -> Iterator[Path]:
    with os.scandir(watch_root) as workspaces:
        for workspace in workspaces:
            if not workspace.is_dir(follow_symlinks=False) or workspace.name.startswith("."):
                continue
            try:
                with os.scandir(workspace.path) as children:
                    for child in children:
                        if (
                            child.is_dir(follow_symlinks=False)
                            and ASSIGNMENT_DIRECTORY.fullmatch(child.name)
                        ):
                            yield Path(child.path)
            except (FileNotFoundError, PermissionError):
                logger.warning(
                    "작업공간을 스캔하지 못함",
                    workspace=workspace.path,
                    exc_info=True,
                )


def scan_source_files(
    watch_root: Path, path_filter: PathFilter
) -> dict[str, FileSignature]:
    """Scan only immutable V2 assignment paths instead of walking the whole NFS tree."""
    result: dict[str, FileSignature] = {}
    for assignment_directory in _assignment_directories(watch_root):
        for directory, directory_names, file_names in os.walk(
            assignment_directory, followlinks=False
        ):
            directory_path = Path(directory)
            relative_depth = len(directory_path.relative_to(watch_root).parts)
            directory_names[:] = [
                name
                for name in directory_names
                if relative_depth < 5 and not _is_pruned_directory(name)
            ]
            for file_name in file_names:
                path = directory_path / file_name
                path_string = str(path)
                if not path_filter.should_process(path_string):
                    continue
                descriptor = None
                try:
                    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
                    descriptor = os.open(path, flags)
                    stat = os.fstat(descriptor)
                except OSError:
                    continue
                finally:
                    if descriptor is not None:
                        os.close(descriptor)
                if not stat_module.S_ISREG(stat.st_mode):
                    continue
                result[path_string] = FileSignature(
                    mtime_ns=stat.st_mtime_ns,
                    size=stat.st_size,
                    inode=stat.st_ino,
                )
    return result


def changed_events(
    previous: dict[str, FileSignature], current: dict[str, FileSignature]
) -> Iterator[FileSystemEvent]:
    for path in sorted(previous.keys() - current.keys()):
        yield FileDeletedEvent(path)
    for path in sorted(current.keys()):
        if path not in previous or current[path] != previous[path]:
            yield FileModifiedEvent(path)


class SelectivePollingObserver:
    """Observer-compatible NFS watcher for V2 assignment directories."""

    def __init__(
        self,
        watch_root: Path,
        handler,
        path_filter: PathFilter,
        interval_seconds: float,
    ):
        self.watch_root = watch_root
        self.handler = handler
        self.path_filter = path_filter
        self.interval_seconds = interval_seconds
        self._stop_event = threading.Event()
        self._baseline_ready = threading.Event()
        self._startup_error: Exception | None = None
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("Polling observer has already been started")
        self._thread = threading.Thread(
            target=self._run,
            name="filemon-nfs-polling",
            daemon=True,
        )
        self._thread.start()
        if not self._baseline_ready.wait(timeout=30):
            self.stop()
            raise TimeoutError("Polling observer baseline scan timed out")
        if self._startup_error is not None:
            raise RuntimeError("Polling observer baseline scan failed") from self._startup_error

    def stop(self) -> None:
        self._stop_event.set()

    def join(self, timeout: float | None = None) -> None:
        if self._thread is not None:
            self._thread.join(timeout)

    def is_alive(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def _run(self) -> None:
        try:
            previous = scan_source_files(self.watch_root, self.path_filter)
        except Exception as error:
            self._startup_error = error
            self._baseline_ready.set()
            logger.critical(
                "NFS 선택적 폴링 기준 상태 생성 실패",
                watch_root=str(self.watch_root),
                exc_info=True,
            )
            return
        self._baseline_ready.set()
        logger.info(
            "NFS 선택적 폴링 기준 상태 생성",
            watch_root=str(self.watch_root),
            source_files=len(previous),
            interval_seconds=self.interval_seconds,
        )
        while not self._stop_event.wait(self.interval_seconds):
            try:
                current = scan_source_files(self.watch_root, self.path_filter)
            except Exception:
                logger.critical(
                    "NFS 선택적 폴링 스캔 실패",
                    watch_root=str(self.watch_root),
                    exc_info=True,
                )
                return
            for event in changed_events(previous, current):
                if event.event_type == "deleted":
                    self.handler.on_deleted(event)
                else:
                    self.handler.on_modified(event)
            previous = current
