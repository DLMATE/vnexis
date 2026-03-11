import threading
from concurrent.futures import ThreadPoolExecutor


class BackgroundExecutor:
    def __init__(self, max_workers: int = 1, thread_name_prefix: str = ""):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix=thread_name_prefix
        )
        self._pause_event = threading.Event()
        self._pause_event.set()

    def __del__(self):
        self.shutdown()

    def submit(self, fn, *args):
        self._executor.submit(self._wrapper, fn, *args)

    def pause(self):
        self._pause_event.clear()

    def resume(self):
        self._pause_event.set()

    def is_running(self) -> bool:
        return self._pause_event.is_set()

    def shutdown(self, wait: bool = True, cancel_futures: bool = True):
        self._executor.shutdown(wait=wait, cancel_futures=cancel_futures)

    def _wrapper(self, fn, *args):
        self._pause_event.wait()
        fn(*args)
