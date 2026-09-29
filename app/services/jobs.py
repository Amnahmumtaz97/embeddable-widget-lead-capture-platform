import logging
from threading import Event, Thread

from app.config import Settings


logger = logging.getLogger("lead_capture.jobs")


class ConsoleNotifier:
    def __init__(self, force_failure: bool = False):
        self.force_failure = force_failure

    def send(self, job: dict) -> None:
        if self.force_failure:
            raise RuntimeError("Forced notification failure")
        logger.info("submission_notification payload=%s", job["payload"])


class JobWorker:
    def __init__(self, repository, notifier: ConsoleNotifier, settings: Settings):
        self.repository = repository
        self.notifier = notifier
        self.settings = settings
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._thread = Thread(target=self._run, name="side-effect-worker", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=3)

    def _run(self) -> None:
        while not self._stop.wait(self.settings.worker_poll_seconds):
            try:
                self.process_once()
            except Exception:
                logger.exception("background_worker_poll_failed")

    def process_once(self) -> int:
        processed = 0
        for job in self.repository.claim_jobs():
            try:
                self.notifier.send(job)
                self.repository.complete_job(job["id"])
            except Exception as exc:
                terminal = job["attempts"] >= job["max_attempts"]
                self.repository.fail_job(job["id"], str(exc), terminal)
                if terminal:
                    logger.error("ALERT side_effect_job_exhausted job_id=%s error=%s", job["id"], exc)
            processed += 1
        return processed
