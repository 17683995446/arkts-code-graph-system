import asyncio
import threading
import time
from pathlib import Path
from typing import Callable, Optional, Set, Dict
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent
import structlog

logger = structlog.get_logger()


class Debouncer:
    def __init__(self, delay: float = 1.0):
        self.delay = delay
        self._timers: Dict[str, Optional[threading.Timer]] = {}
        self._lock = threading.Lock()
        self._pending_files: Set[str] = set()

    def debounce(self, file_path: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            if file_path in self._timers and self._timers[file_path] is not None:
                self._timers[file_path].cancel()

            self._pending_files.add(file_path)

            timer = threading.Timer(self.delay, self._execute_callback, args=(file_path, callback))
            self._timers[file_path] = timer
            timer.start()

    def _execute_callback(self, file_path: str, callback: Callable[[str], None]) -> None:
        with self._lock:
            self._timers[file_path] = None
            if file_path in self._pending_files:
                self._pending_files.discard(file_path)

        try:
            callback(file_path)
        except Exception as e:
            logger.error("debouncer_callback_error", file_path=file_path, error=str(e))

    def cancel_all(self) -> None:
        with self._lock:
            for timer in self._timers.values():
                if timer is not None:
                    timer.cancel()
            self._timers.clear()
            self._pending_files.clear()

    def is_pending(self, file_path: str) -> bool:
        with self._lock:
            return file_path in self._pending_files


class FileEventHandler(FileSystemEventHandler):
    def __init__(self, callback: Callable[[str], None], exclude_patterns: list[str]):
        super().__init__()
        self.callback = callback
        self.exclude_patterns = exclude_patterns
        self._debouncer = Debouncer()

    def _should_process(self, path: str) -> bool:
        path_obj = Path(path)
        for pattern in self.exclude_patterns:
            if path_obj.match(pattern):
                return False
        return True

    def on_modified(self, event):
        if event.is_directory:
            return
        if isinstance(event, FileModifiedEvent) and self._should_process(event.src_path):
            logger.debug("file_modified_detected", path=event.src_path)
            self._debouncer.debounce(event.src_path, self.callback)

    def on_created(self, event):
        if event.is_directory:
            return
        if isinstance(event, FileCreatedEvent) and self._should_process(event.src_path):
            logger.debug("file_created_detected", path=event.src_path)
            self._debouncer.debounce(event.src_path, self.callback)

    def on_deleted(self, event):
        if event.is_directory:
            return
        logger.info("file_deleted", path=event.src_path)


class FileWatcher:
    def __init__(
        self,
        root_dir: str,
        callback: Callable[[str], None],
        file_pattern: str = "**/*.ets",
        exclude_patterns: Optional[list[str]] = None,
        debounce_delay: float = 1.0
    ):
        self.root_dir = root_dir
        self.callback = callback
        self.file_pattern = file_pattern
        self.exclude_patterns = exclude_patterns or []
        self.debounce_delay = debounce_delay

        self._observer: Optional[Observer] = None
        self._handler: Optional[FileEventHandler] = None
        self._is_running = False

        logger.info(
            "file_watcher_initialized",
            root_dir=root_dir,
            pattern=file_pattern,
            exclude=exclude_patterns
        )

    def start(self) -> None:
        if self._is_running:
            logger.warning("file_watcher_already_running")
            return

        self._handler = FileEventHandler(
            callback=self.callback,
            exclude_patterns=self.exclude_patterns
        )

        self._observer = Observer()
        self._observer.schedule(
            self._handler,
            self.root_dir,
            recursive=True
        )
        self._observer.start()
        self._is_running = True

        logger.info("file_watcher_started", root_dir=self.root_dir)

    def stop(self) -> None:
        if not self._is_running:
            return

        if self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None

        if self._handler:
            self._handler._debouncer.cancel_all()
            self._handler = None

        self._is_running = False
        logger.info("file_watcher_stopped")

    def watch_forever(self) -> None:
        self.start()
        try:
            while self._is_running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("file_watcher_interrupted")
        finally:
            self.stop()

    def is_running(self) -> bool:
        return self._is_running
