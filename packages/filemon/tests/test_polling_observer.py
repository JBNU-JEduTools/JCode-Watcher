import os
import threading
from pathlib import Path

from watchdog.events import FileDeletedEvent, FileModifiedEvent

from app.polling_observer import (
    FileSignature,
    SelectivePollingObserver,
    changed_events,
    scan_source_files,
)


class AllowPythonFiles:
    def should_process(self, path: str) -> bool:
        return path.endswith(".py")


def test_scan_only_visits_v2_assignment_source_paths(tmp_path: Path):
    accepted = tmp_path / "course-1-202117547" / "assignment-53" / "src" / "main.py"
    accepted.parent.mkdir(parents=True)
    accepted.write_text("print('ok')", encoding="utf-8")
    (accepted.parent / "notes.txt").write_text("skip", encoding="utf-8")

    legacy = tmp_path / "course-1-202117547" / "과제명" / "legacy.py"
    legacy.parent.mkdir(parents=True)
    legacy.write_text("skip", encoding="utf-8")

    dependency = (
        tmp_path
        / "course-1-202117547"
        / "assignment-53"
        / "node_modules"
        / "package.py"
    )
    dependency.parent.mkdir(parents=True)
    dependency.write_text("skip", encoding="utf-8")

    snapshot = scan_source_files(tmp_path, AllowPythonFiles())

    assert set(snapshot) == {str(accepted)}


def test_changed_events_maps_create_modify_and_delete():
    deleted = "/watcher/codes/course-1-user/assignment-1/deleted.py"
    modified = "/watcher/codes/course-1-user/assignment-1/modified.py"
    created = "/watcher/codes/course-1-user/assignment-1/created.py"
    unchanged = "/watcher/codes/course-1-user/assignment-1/unchanged.py"
    old = FileSignature(mtime_ns=1, size=1, inode=1)
    new = FileSignature(mtime_ns=2, size=1, inode=1)

    events = list(
        changed_events(
            {deleted: old, modified: old, unchanged: old},
            {modified: new, created: new, unchanged: old},
        )
    )

    assert [(type(event), event.src_path) for event in events] == [
        (FileDeletedEvent, deleted),
        (FileModifiedEvent, created),
        (FileModifiedEvent, modified),
    ]


def test_scan_detects_a_same_size_atomic_replacement(tmp_path: Path):
    source = tmp_path / "course-1-202117547" / "assignment-53" / "main.py"
    source.parent.mkdir(parents=True)
    source.write_text("one", encoding="utf-8")
    before = scan_source_files(tmp_path, AllowPythonFiles())

    replacement = source.with_suffix(".tmp")
    replacement.write_text("two", encoding="utf-8")
    os.replace(replacement, source)
    after = scan_source_files(tmp_path, AllowPythonFiles())

    assert list(changed_events(before, after))[0].src_path == str(source)


def test_observer_uses_the_first_scan_as_a_baseline(tmp_path: Path):
    source = tmp_path / "course-1-202117547" / "assignment-53" / "main.py"
    source.parent.mkdir(parents=True)
    source.write_text("before", encoding="utf-8")

    class RecordingHandler:
        def __init__(self):
            self.modified = []
            self.received = threading.Event()

        def on_modified(self, event):
            self.modified.append(event.src_path)
            self.received.set()

        def on_deleted(self, event):
            raise AssertionError(f"unexpected deletion: {event.src_path}")

    handler = RecordingHandler()
    observer = SelectivePollingObserver(
        watch_root=tmp_path,
        handler=handler,
        path_filter=AllowPythonFiles(),
        interval_seconds=0.01,
    )

    observer.start()
    assert handler.modified == []
    source.write_text("after", encoding="utf-8")
    assert handler.received.wait(timeout=1)
    observer.stop()
    observer.join(timeout=1)

    assert handler.modified == [str(source)]
    assert not observer.is_alive()
